#!/usr/bin/env python
"""WebSocket Connection Stability Stress Tests

Business Value: Platform stability under load
Tests: Connection resilience, memory management, concurrent load handling

This suite ensures WebSocket connections remain stable under:
1. High concurrent connection load
2. Rapid connect/disconnect cycles
3. Memory pressure scenarios
4. Network instability simulation
5. Long-running connections
"""

import asyncio
import gc
import json
import os
import psutil
import random
import sys
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Any, Optional, Tuple
import tracemalloc
from shared.isolated_environment import IsolatedEnvironment

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import production components
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.websocket_core.manager import WebSocketHeartbeatManager, HeartbeatConfig
from netra_backend.app.websocket_core.rate_limiter import get_rate_limiter
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from fastapi import WebSocket
from fastapi.websockets import WebSocketState


# ============================================================================
# STRESS TEST UTILITIES
# ============================================================================

class StressTestMetrics:
    """Collect and analyze stress test metrics."""
    
    def __init__(self):
        self.start_time = time.time()
        self.connections_created = 0
        self.connections_closed = 0
        self.connections_failed = 0
        self.messages_sent = 0
        self.messages_failed = 0
        self.max_concurrent_connections = 0
        self.memory_samples: List[float] = []
        self.latency_samples: List[float] = []
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.connection_durations: List[float] = []
        
    def record_connection_created(self):
        self.connections_created += 1
        
    def record_connection_closed(self, duration: float):
        self.connections_closed += 1
        self.connection_durations.append(duration)
        
    def record_connection_failed(self, error: str):
        self.connections_failed += 1
        self.error_counts[error] += 1
        
    def record_message_sent(self, latency: float):
        self.messages_sent += 1
        self.latency_samples.append(latency)
        
    def record_message_failed(self):
        self.messages_failed += 1
        
    def update_concurrent_connections(self, count: int):
        self.max_concurrent_connections = max(self.max_concurrent_connections, count)
        
    def sample_memory(self):
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        self.memory_samples.append(memory_mb)
        return memory_mb
        
    def get_summary(self) -> Dict[str, Any]:
        """Generate comprehensive metrics summary."""
        duration = time.time() - self.start_time
        
        return {
            "duration_seconds": duration,
            "connections": {
                "created": self.connections_created,
                "closed": self.connections_closed,
                "failed": self.connections_failed,
                "max_concurrent": self.max_concurrent_connections,
                "success_rate": (self.connections_created - self.connections_failed) / max(1, self.connections_created)
            },
            "messages": {
                "sent": self.messages_sent,
                "failed": self.messages_failed,
                "throughput_per_second": self.messages_sent / max(1, duration),
                "success_rate": self.messages_sent / max(1, self.messages_sent + self.messages_failed)
            },
            "performance": {
                "avg_latency_ms": sum(self.latency_samples) / max(1, len(self.latency_samples)) * 1000 if self.latency_samples else 0,
                "p95_latency_ms": sorted(self.latency_samples)[int(len(self.latency_samples) * 0.95)] * 1000 if self.latency_samples else 0,
                "p99_latency_ms": sorted(self.latency_samples)[int(len(self.latency_samples) * 0.99)] * 1000 if self.latency_samples else 0,
                "avg_connection_duration_s": sum(self.connection_durations) / max(1, len(self.connection_durations)) if self.connection_durations else 0
            },
            "memory": {
                "initial_mb": self.memory_samples[0] if self.memory_samples else 0,
                "peak_mb": max(self.memory_samples) if self.memory_samples else 0,
                "final_mb": self.memory_samples[-1] if self.memory_samples else 0,
                "growth_mb": (self.memory_samples[-1] - self.memory_samples[0]) if self.memory_samples else 0
            },
            "errors": dict(self.error_counts)
        }


class SimulatedWebSocket:
    """Simulated WebSocket for stress testing."""
    
    def __init__(self, connection_id: str, network_profile: str = "stable"):
        self.connection_id = connection_id
        self.client_state = WebSocketState.CONNECTED
        self.application_state = WebSocketState.CONNECTED
        self.network_profile = network_profile
        self.message_buffer: List[Dict] = []
        self.send_count = 0
        self.error_count = 0
        self.created_at = time.time()
        
        # Network profiles
        self.profiles = {
            "stable": {"latency": 0.001, "packet_loss": 0.0, "jitter": 0.0},
            "unstable": {"latency": 0.05, "packet_loss": 0.05, "jitter": 0.02},
            "poor": {"latency": 0.2, "packet_loss": 0.1, "jitter": 0.1},
            "terrible": {"latency": 0.5, "packet_loss": 0.2, "jitter": 0.3}
        }
        
    async def send_json(self, data: Dict[str, Any]) -> None:
        """Simulate sending with network conditions."""
        profile = self.profiles.get(self.network_profile, self.profiles["stable"])
        
        # Simulate network latency with jitter
        latency = profile["latency"] + random.uniform(-profile["jitter"], profile["jitter"])
        if latency > 0:
            await asyncio.sleep(latency)
        
        # Simulate packet loss
        if random.random() < profile["packet_loss"]:
            self.error_count += 1
            raise ConnectionError(f"Simulated packet loss (profile: {self.network_profile})")
        
        # Simulate connection state issues
        if self.client_state != WebSocketState.CONNECTED:
            raise ConnectionError("Connection not in CONNECTED state")
        
        self.message_buffer.append(data)
        self.send_count += 1
        
    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Simulate closing connection."""
        self.client_state = WebSocketState.DISCONNECTED
        self.application_state = WebSocketState.DISCONNECTED
        
    def get_lifetime(self) -> float:
        """Get connection lifetime in seconds."""
        return time.time() - self.created_at


# ============================================================================
# STRESS TEST SUITE
# ============================================================================

class TestWebSocketConnectionStability:
    """Stress tests for WebSocket connection stability."""
    
    @pytest.fixture(autouse=True)
    async def setup_stress_environment(self):
        """Setup stress test environment."""
        self.ws_manager = WebSocketManager()
        self.heartbeat_manager = WebSocketHeartbeatManager(
            HeartbeatConfig(
                heartbeat_interval_seconds=10,
                heartbeat_timeout_seconds=30,
                max_missed_heartbeats=3
            )
        )
        self.metrics = StressTestMetrics()
        
        # Start memory tracking
        tracemalloc.start()
        self.metrics.sample_memory()
        
        yield
        
        # Cleanup
        await self.cleanup_all_connections()
        tracemalloc.stop()
        
    async def cleanup_all_connections(self):
        """Clean up all test connections."""
        for conn_id in list(self.ws_manager.connections.keys()):
            try:
                conn = self.ws_manager.connections[conn_id]
                ws = conn.get("websocket")
                if ws:
                    await ws.close()
            except Exception:
                pass
        self.ws_manager.connections.clear()
        
    async def create_connection(self, user_id: str, thread_id: str, 
                               network_profile: str = "stable") -> Tuple[str, SimulatedWebSocket]:
        """Create a simulated connection."""
        conn_id = f"stress_{user_id}_{uuid.uuid4().hex[:8]}"
        mock_ws = SimulatedWebSocket(conn_id, network_profile)
        
        # Add to manager
        self.ws_manager.connections[conn_id] = {
            "connection_id": conn_id,
            "user_id": user_id,
            "websocket": mock_ws,
            "thread_id": thread_id,
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "message_count": 0,
            "is_healthy": True
        }
        
        # Track user connections
        if user_id not in self.ws_manager.user_connections:
            self.ws_manager.user_connections[user_id] = set()
        self.ws_manager.user_connections[user_id].add(conn_id)
        
        self.metrics.record_connection_created()
        self.metrics.update_concurrent_connections(len(self.ws_manager.connections))
        
        return conn_id, mock_ws
    
    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_high_concurrent_connections(self):
        """Test system behavior with many concurrent connections."""
        target_connections = 500  # Stress test with 500 connections
        connections = {}
        
        logger.info(f"Creating {target_connections} concurrent connections...")
        
        # Create connections in batches to avoid overwhelming
        batch_size = 50
        for batch_start in range(0, target_connections, batch_size):
            batch_tasks = []
            for i in range(batch_start, min(batch_start + batch_size, target_connections)):
                user_id = f"stress_user_{i}"
                thread_id = f"stress_thread_{i % 10}"  # 10 threads total
                
                async def create_conn(uid, tid):
                    try:
                        conn_id, mock_ws = await self.create_connection(uid, tid, "stable")
                        return conn_id, mock_ws
                    except Exception as e:
                        self.metrics.record_connection_failed(str(e))
                        return None, None
                
                batch_tasks.append(create_conn(user_id, thread_id))
            
            # Create batch concurrently
            results = await asyncio.gather(*batch_tasks)
            for conn_id, mock_ws in results:
                if conn_id:
                    connections[conn_id] = mock_ws
            
            # Small delay between batches
            await asyncio.sleep(0.1)
            
            # Sample memory
            memory_mb = self.metrics.sample_memory()
            logger.info(f"Batch {batch_start//batch_size + 1}: {len(connections)} connections, Memory: {memory_mb:.1f} MB")
        
        # Send messages to all connections
        logger.info("Sending messages to all connections...")
        notifier = AgentWebSocketBridge(self.ws_manager)
        
        send_tasks = []
        for thread_id in range(10):
            context = AgentExecutionContext(
                run_id=f"stress_run_{thread_id}",
                thread_id=f"stress_thread_{thread_id}",
                user_id=f"stress_user_{thread_id}",
                agent_name="stress_test",
                retry_count=0,
                max_retries=1
            )
            
            async def send_to_thread(ctx):
                start = time.time()
                try:
                    await notifier.send_agent_thinking(ctx, f"Stress test message for thread {ctx.thread_id}")
                    latency = time.time() - start
                    self.metrics.record_message_sent(latency)
                except Exception:
                    self.metrics.record_message_failed()
            
            send_tasks.append(send_to_thread(context))
        
        await asyncio.gather(*send_tasks)
        
        # Verify connections are still healthy
        healthy_count = sum(1 for conn in self.ws_manager.connections.values() if conn.get("is_healthy"))
        
        # Generate report
        summary = self.metrics.get_summary()
        logger.info(f"Stress test summary: {json.dumps(summary, indent=2)}")
        
        # Assertions
        assert healthy_count > target_connections * 0.95, f"Too many unhealthy connections: {healthy_count}/{target_connections}"
        assert summary["memory"]["growth_mb"] < 100, f"Excessive memory growth: {summary['memory']['growth_mb']} MB"
        assert summary["messages"]["success_rate"] > 0.95, f"Low message success rate: {summary['messages']['success_rate']}"
    
    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_rapid_connect_disconnect_cycles(self):
        """Test rapid connection and disconnection cycles."""
        num_cycles = 100
        connections_per_cycle = 20
        
        logger.info(f"Running {num_cycles} connect/disconnect cycles...")
        
        for cycle in range(num_cycles):
            # Create connections
            cycle_connections = []
            for i in range(connections_per_cycle):
                user_id = f"cycle_user_{i}"
                thread_id = f"cycle_thread_{cycle}"
                
                try:
                    conn_id, mock_ws = await self.create_connection(user_id, thread_id, "unstable")
                    cycle_connections.append((conn_id, mock_ws))
                except Exception as e:
                    self.metrics.record_connection_failed(str(e))
            
            # Send a message to each
            for conn_id, mock_ws in cycle_connections:
                try:
                    start = time.time()
                    await self.ws_manager.send_to_thread(f"cycle_thread_{cycle}", {"type": "test", "cycle": cycle})
                    self.metrics.record_message_sent(time.time() - start)
                except Exception:
                    self.metrics.record_message_failed()
            
            # Disconnect all
            for conn_id, mock_ws in cycle_connections:
                try:
                    await mock_ws.close()
                    del self.ws_manager.connections[conn_id]
                    self.metrics.record_connection_closed(mock_ws.get_lifetime())
                except Exception:
                    pass
            
            # Check for memory leaks every 10 cycles
            if cycle % 10 == 0:
                gc.collect()
                memory_mb = self.metrics.sample_memory()
                logger.info(f"Cycle {cycle}: Memory {memory_mb:.1f} MB, Active connections: {len(self.ws_manager.connections)}")
        
        # Final cleanup
        await self.cleanup_all_connections()
        gc.collect()
        
        # Verify no connection leaks
        assert len(self.ws_manager.connections) == 0, f"Connection leak: {len(self.ws_manager.connections)} connections remain"
        
        # Check memory
        summary = self.metrics.get_summary()
        assert summary["memory"]["growth_mb"] < 50, f"Memory leak detected: {summary['memory']['growth_mb']} MB growth"
    
    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_network_instability_resilience(self):
        """Test resilience under various network conditions."""
        network_profiles = ["stable", "unstable", "poor", "terrible"]
        connections_per_profile = 25
        
        logger.info("Testing under various network conditions...")
        
        profile_connections = {}
        
        # Create connections with different network profiles
        for profile in network_profiles:
            profile_connections[profile] = []
            for i in range(connections_per_profile):
                user_id = f"{profile}_user_{i}"
                thread_id = f"{profile}_thread"
                
                try:
                    conn_id, mock_ws = await self.create_connection(user_id, thread_id, profile)
                    profile_connections[profile].append((conn_id, mock_ws))
                except Exception as e:
                    self.metrics.record_connection_failed(f"{profile}: {e}")
        
        # Send messages and measure success rates
        profile_results = {}
        
        for profile, connections in profile_connections.items():
            successes = 0
            failures = 0
            
            for conn_id, mock_ws in connections:
                for _ in range(10):  # 10 messages per connection
                    try:
                        start = time.time()
                        await mock_ws.send_json({"type": "test", "profile": profile})
                        self.metrics.record_message_sent(time.time() - start)
                        successes += 1
                    except Exception:
                        self.metrics.record_message_failed()
                        failures += 1
            
            profile_results[profile] = {
                "success_rate": successes / max(1, successes + failures),
                "total_sent": successes,
                "total_failed": failures
            }
            
            logger.info(f"Profile '{profile}': Success rate {profile_results[profile]['success_rate']:.2%}")
        
        # Verify minimum success rates
        assert profile_results["stable"]["success_rate"] > 0.99, "Stable network should have >99% success"
        assert profile_results["unstable"]["success_rate"] > 0.90, "Unstable network should have >90% success"
        assert profile_results["poor"]["success_rate"] > 0.75, "Poor network should have >75% success"
        # Terrible network can have lower success rate but should not crash
    
    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_long_running_connections(self):
        """Test long-running connections for stability."""
        num_connections = 50
        test_duration_seconds = 30  # Run for 30 seconds
        
        logger.info(f"Testing {num_connections} connections for {test_duration_seconds} seconds...")
        
        # Create long-running connections
        connections = {}
        for i in range(num_connections):
            user_id = f"long_user_{i}"
            thread_id = f"long_thread_{i % 5}"
            
            conn_id, mock_ws = await self.create_connection(user_id, thread_id, "stable")
            connections[conn_id] = mock_ws
        
        # Send periodic messages
        start_time = time.time()
        message_interval = 1.0  # Send message every second
        
        while time.time() - start_time < test_duration_seconds:
            # Send messages to all threads
            send_tasks = []
            for thread_num in range(5):
                thread_id = f"long_thread_{thread_num}"
                
                async def send_periodic(tid):
                    try:
                        await self.ws_manager.send_to_thread(tid, {
                            "type": "heartbeat",
                            "timestamp": time.time(),
                            "thread": tid
                        })
                        self.metrics.record_message_sent(0.001)  # Assume low latency
                    except Exception:
                        self.metrics.record_message_failed()
                
                send_tasks.append(send_periodic(thread_id))
            
            await asyncio.gather(*send_tasks)
            
            # Sample memory
            if int(time.time() - start_time) % 5 == 0:
                memory_mb = self.metrics.sample_memory()
                healthy = sum(1 for c in self.ws_manager.connections.values() if c.get("is_healthy"))
                logger.info(f"Time {int(time.time() - start_time)}s: Memory {memory_mb:.1f} MB, Healthy: {healthy}/{num_connections}")
            
            await asyncio.sleep(message_interval)
        
        # Check final state
        healthy_count = sum(1 for conn in self.ws_manager.connections.values() if conn.get("is_healthy"))
        
        summary = self.metrics.get_summary()
        logger.info(f"Long-running test summary: {json.dumps(summary, indent=2)}")
        
        # Assertions
        assert healthy_count >= num_connections * 0.95, f"Too many connections died: {healthy_count}/{num_connections}"
        assert summary["memory"]["growth_mb"] < 20, f"Memory growth during long run: {summary['memory']['growth_mb']} MB"
    
    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_message_buffer_overflow(self):
        """Test behavior when message buffers overflow."""
        num_connections = 100
        messages_per_connection = 1000  # Flood with messages
        
        logger.info(f"Testing message buffer overflow with {num_connections} connections...")
        
        # Create connections
        connections = []
        for i in range(num_connections):
            user_id = f"buffer_user_{i}"
            thread_id = f"buffer_thread_{i % 10}"
            
            conn_id, mock_ws = await self.create_connection(user_id, thread_id, "stable")
            # Simulate slow consumer
            mock_ws.network_profile = "poor"
            connections.append((conn_id, mock_ws, thread_id))
        
        # Flood with messages
        notifier = AgentWebSocketBridge(self.ws_manager)
        
        flood_start = time.time()
        send_tasks = []
        
        for i in range(messages_per_connection):
            for thread_num in range(10):
                context = AgentExecutionContext(
                    run_id=f"flood_{i}_{thread_num}",
                    thread_id=f"buffer_thread_{thread_num}",
                    user_id=f"buffer_user_{thread_num}",
                    agent_name="flood_test",
                    retry_count=0,
                    max_retries=1
                )
                
                async def flood_send(ctx, msg_num):
                    try:
                        await notifier.send_agent_thinking(ctx, f"Flood message {msg_num}")
                        self.metrics.record_message_sent(0.001)
                    except Exception:
                        self.metrics.record_message_failed()
                
                send_tasks.append(flood_send(context, i))
            
            # Send in batches to avoid overwhelming
            if len(send_tasks) >= 100:
                await asyncio.gather(*send_tasks)
                send_tasks = []
        
        # Send remaining
        if send_tasks:
            await asyncio.gather(*send_tasks)
        
        flood_duration = time.time() - flood_start
        messages_per_second = (messages_per_connection * 10) / flood_duration
        
        logger.info(f"Sent {messages_per_connection * 10} messages in {flood_duration:.2f}s ({messages_per_second:.0f} msg/s)")
        
        # Check system didn't crash
        healthy_count = sum(1 for conn in self.ws_manager.connections.values() if conn.get("is_healthy"))
        
        # Verify system handled overflow gracefully
        assert healthy_count > 0, "All connections died during flood"
        assert self.metrics.messages_sent > 0, "No messages were sent successfully"
        
        summary = self.metrics.get_summary()
        logger.info(f"Buffer overflow test summary: {json.dumps(summary, indent=2)}")
    
    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_connection_limit_enforcement(self):
        """Test that connection limits are properly enforced."""
        max_per_user = self.ws_manager.MAX_CONNECTIONS_PER_USER
        max_total = self.ws_manager.MAX_TOTAL_CONNECTIONS
        
        logger.info(f"Testing connection limits: {max_per_user} per user, {max_total} total...")
        
        # Test per-user limit
        user_id = "limit_test_user"
        user_connections = []
        
        for i in range(max_per_user + 5):  # Try to exceed limit
            try:
                conn_id, mock_ws = await self.create_connection(user_id, f"thread_{i}", "stable")
                user_connections.append(conn_id)
            except Exception:
                pass  # Expected when limit exceeded
        
        # Check user connection count
        actual_user_conns = len(self.ws_manager.user_connections.get(user_id, set()))
        assert actual_user_conns <= max_per_user, f"Per-user limit not enforced: {actual_user_conns} > {max_per_user}"
        
        # Test total limit (if not already exceeded)
        if len(self.ws_manager.connections) < max_total:
            remaining = max_total - len(self.ws_manager.connections)
            
            for i in range(remaining + 10):  # Try to exceed total limit
                try:
                    user_id = f"total_limit_user_{i}"
                    await self.create_connection(user_id, f"thread_{i}", "stable")
                except Exception:
                    pass  # Expected when limit exceeded
        
        # Check total connection count
        total_conns = len(self.ws_manager.connections)
        assert total_conns <= max_total, f"Total limit not enforced: {total_conns} > {max_total}"
        
        logger.info(f"Connection limits properly enforced: {total_conns} total connections")


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    # Run with: python tests/stress/test_websocket_connection_stability.py
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "stress"])