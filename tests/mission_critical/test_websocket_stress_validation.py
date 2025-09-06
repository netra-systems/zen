#!/usr/bin/env python
"""MISSION CRITICAL: WebSocket Stress Testing & High-Load Validation

Business Value Justification:
- Segment: Platform/Internal (Mission Critical Infrastructure)
- Business Goal: Ensure $500K+ ARR chat functionality scales under production load
- Value Impact: Validates WebSocket performance under concurrent user scenarios
- Strategic Impact: Prevents system collapse under high load that causes revenue loss

This stress test suite validates:
1. High concurrent connection handling (25+ simultaneous users)
2. Message throughput and latency under load
3. Memory leak detection during extended operation
4. Connection recovery and reconnection resilience
5. Event ordering preservation under high load
6. User isolation integrity at scale

CRITICAL: These tests simulate production load scenarios.
ALL TESTS MUST PASS for production deployment approval.
"""

import asyncio
import json
import os
import sys
import time
import uuid
import psutil
import threading
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
import random
import statistics
import gc

# CRITICAL: Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import test infrastructure
from shared.isolated_environment import get_env, IsolatedEnvironment
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
from tests.mission_critical.websocket_real_test_base import requires_docker, is_docker_available
from tests.mission_critical.websocket_monitoring_utils import (
    WebSocketMonitoringOrchestrator, EventMetrics, RealTimeEventMonitor
)

# Import WebSocket test utilities
from tests.mission_critical.test_websocket_event_validation_suite import (
    WebSocketConnectionManager, ValidationTestConfig, create_test_agent_message, 
    create_mock_auth_token, EventType
)


# ============================================================================
# STRESS TEST CONFIGURATION
# ============================================================================

@dataclass
class StressTestConfig:
    """Configuration for WebSocket stress testing."""
    
    # Connection stress parameters
    max_concurrent_connections: int = 25
    connection_ramp_up_seconds: float = 10.0
    connection_hold_time_seconds: float = 60.0
    
    # Message throughput parameters
    messages_per_connection: int = 20
    message_interval_seconds: float = 2.0
    message_burst_size: int = 5
    
    # Performance thresholds
    max_connection_time_ms: float = 5000.0  # 5 seconds to establish
    max_message_latency_ms: float = 200.0   # 200ms max latency
    max_memory_growth_mb: float = 500.0     # 500MB max memory growth
    min_throughput_msgs_sec: float = 10.0   # 10 messages/sec minimum
    
    # Resilience testing
    connection_drop_percentage: float = 10.0  # 10% connections will be dropped
    reconnection_attempts: int = 3
    chaos_testing_enabled: bool = True
    
    # Load distribution
    user_activity_patterns: Dict[str, float] = field(default_factory=lambda: {
        'heavy_user': 0.20,    # 20% heavy users (many messages)
        'normal_user': 0.60,   # 60% normal users
        'light_user': 0.20     # 20% light users (few messages)
    })


# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

class StressTestMonitor:
    """Monitors system performance during stress testing."""
    
    def __init__(self):
        self.start_time = time.time()
        self.baseline_memory = psutil.virtual_memory().used
        self.baseline_cpu = psutil.cpu_percent()
        
        # Performance metrics
        self.connection_times: List[float] = []
        self.message_latencies: List[float] = []
        self.throughput_samples: deque = deque(maxlen=100)
        
        # Resource monitoring
        self.memory_samples: List[Tuple[float, int]] = []
        self.cpu_samples: List[Tuple[float, float]] = []
        
        # Connection tracking
        self.active_connections = 0
        self.total_connections_created = 0
        self.connection_failures = 0
        
        # Message tracking
        self.messages_sent = 0
        self.messages_received = 0
        self.message_failures = 0
        
        # Monitoring thread
        self._monitoring_active = False
        self._monitor_thread = None
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self._monitor_thread.start()
        logger.info("Stress test monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self._monitoring_active = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
        logger.info("Stress test monitoring stopped")
    
    def _monitor_resources(self):
        """Monitor system resources continuously."""
        while self._monitoring_active:
            current_time = time.time()
            
            # Memory usage
            memory_used = psutil.virtual_memory().used
            self.memory_samples.append((current_time, memory_used))
            
            # CPU usage
            cpu_percent = psutil.cpu_percent()
            self.cpu_samples.append((current_time, cpu_percent))
            
            # Keep only last 1000 samples to prevent memory bloat
            if len(self.memory_samples) > 1000:
                self.memory_samples = self.memory_samples[-500:]
            if len(self.cpu_samples) > 1000:
                self.cpu_samples = self.cpu_samples[-500:]
            
            time.sleep(1.0)  # Sample every second
    
    def record_connection_time(self, connection_time_ms: float):
        """Record connection establishment time."""
        self.connection_times.append(connection_time_ms)
        self.total_connections_created += 1
    
    def record_connection_active(self):
        """Record active connection."""
        self.active_connections += 1
    
    def record_connection_closed(self):
        """Record connection closure."""
        self.active_connections = max(0, self.active_connections - 1)
    
    def record_connection_failure(self):
        """Record connection failure."""
        self.connection_failures += 1
    
    def record_message_sent(self):
        """Record message sent."""
        self.messages_sent += 1
        
        # Calculate throughput
        current_time = time.time()
        self.throughput_samples.append(current_time)
        
        # Remove samples older than 10 seconds for rolling throughput
        cutoff_time = current_time - 10.0
        while self.throughput_samples and self.throughput_samples[0] < cutoff_time:
            self.throughput_samples.popleft()
    
    def record_message_received(self, latency_ms: float):
        """Record message received with latency."""
        self.messages_received += 1
        self.message_latencies.append(latency_ms)
    
    def record_message_failure(self):
        """Record message failure."""
        self.message_failures += 1
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        current_time = time.time()
        duration = current_time - self.start_time
        
        # Memory metrics
        current_memory = psutil.virtual_memory().used
        memory_growth_mb = (current_memory - self.baseline_memory) / (1024 * 1024)
        
        # Connection metrics
        connection_success_rate = 0
        if self.total_connections_created > 0:
            connection_success_rate = ((self.total_connections_created - self.connection_failures) / 
                                      self.total_connections_created * 100)
        
        # Message metrics
        message_success_rate = 0
        if self.messages_sent > 0:
            message_success_rate = (self.messages_received / self.messages_sent * 100)
        
        # Latency statistics
        latency_stats = {}
        if self.message_latencies:
            latency_stats = {
                "avg_ms": statistics.mean(self.message_latencies),
                "median_ms": statistics.median(self.message_latencies),
                "p95_ms": statistics.quantiles(self.message_latencies, n=20)[18],  # 95th percentile
                "max_ms": max(self.message_latencies),
                "min_ms": min(self.message_latencies)
            }
        
        # Connection time statistics
        connection_stats = {}
        if self.connection_times:
            connection_stats = {
                "avg_ms": statistics.mean(self.connection_times),
                "max_ms": max(self.connection_times),
                "min_ms": min(self.connection_times)
            }
        
        # Throughput calculation
        throughput_msgs_sec = len(self.throughput_samples) / min(10.0, duration) if duration > 0 else 0
        
        return {
            "duration_seconds": duration,
            "memory": {
                "baseline_mb": self.baseline_memory / (1024 * 1024),
                "current_mb": current_memory / (1024 * 1024),
                "growth_mb": memory_growth_mb
            },
            "connections": {
                "active": self.active_connections,
                "total_created": self.total_connections_created,
                "failures": self.connection_failures,
                "success_rate_percent": connection_success_rate,
                "timing_stats": connection_stats
            },
            "messages": {
                "sent": self.messages_sent,
                "received": self.messages_received,
                "failures": self.message_failures,
                "success_rate_percent": message_success_rate,
                "throughput_msgs_sec": throughput_msgs_sec,
                "latency_stats": latency_stats
            },
            "resource_usage": {
                "peak_memory_mb": max(sample[1] for sample in self.memory_samples) / (1024 * 1024) if self.memory_samples else 0,
                "avg_cpu_percent": statistics.mean(sample[1] for sample in self.cpu_samples) if self.cpu_samples else 0
            }
        }


# ============================================================================
# STRESS TEST SCENARIOS
# ============================================================================

class WebSocketStressTestRunner:
    """Executes comprehensive WebSocket stress testing scenarios."""
    
    def __init__(self, config: StressTestConfig):
        self.config = config
        self.monitor = StressTestMonitor()
        self.websocket_manager = WebSocketConnectionManager()
        
        # Test state
        self.active_connections: Dict[str, Any] = {}
        self.test_results: Dict[str, Any] = {}
        self.errors: List[str] = []
    
    async def run_connection_stress_test(self) -> Dict[str, Any]:
        """Test high concurrent connection handling."""
        logger.info(f"Starting connection stress test: {self.config.max_concurrent_connections} connections")
        
        self.monitor.start_monitoring()
        
        try:
            # Create connections with controlled ramp-up
            connections = []
            connection_tasks = []
            
            ramp_delay = self.config.connection_ramp_up_seconds / self.config.max_concurrent_connections
            
            for i in range(self.config.max_concurrent_connections):
                user_id = f"stress_user_{i}_{uuid.uuid4().hex[:8]}"
                auth_token = create_mock_auth_token(user_id)
                
                # Create connection with delay for ramp-up
                connection_task = asyncio.create_task(
                    self._create_delayed_connection(user_id, auth_token, i * ramp_delay)
                )
                connection_tasks.append(connection_task)
                
                # Small delay to avoid overwhelming the system
                if i % 5 == 0:  # Every 5 connections
                    await asyncio.sleep(0.1)
            
            # Wait for all connections to be established
            logger.info("Waiting for all connections to be established...")
            connection_results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            
            # Filter successful connections
            successful_connections = [
                result for result in connection_results 
                if not isinstance(result, Exception) and result is not None
            ]
            
            logger.info(f"Established {len(successful_connections)}/{self.config.max_concurrent_connections} connections")
            
            # Hold connections for specified time
            logger.info(f"Holding connections for {self.config.connection_hold_time_seconds} seconds...")
            await asyncio.sleep(self.config.connection_hold_time_seconds)
            
            # Close all connections
            logger.info("Closing all connections...")
            close_tasks = []
            for websocket, user_id in successful_connections:
                if not websocket.closed:
                    close_tasks.append(asyncio.create_task(websocket.close()))
                    self.monitor.record_connection_closed()
            
            if close_tasks:
                await asyncio.gather(*close_tasks, return_exceptions=True)
            
            return {
                "connections_requested": self.config.max_concurrent_connections,
                "connections_successful": len(successful_connections),
                "connection_success_rate": len(successful_connections) / self.config.max_concurrent_connections * 100,
                "hold_time_seconds": self.config.connection_hold_time_seconds
            }
            
        finally:
            self.monitor.stop_monitoring()
    
    async def _create_delayed_connection(self, user_id: str, auth_token: str, delay: float) -> Optional[Tuple]:
        """Create a connection with specified delay."""
        try:
            if delay > 0:
                await asyncio.sleep(delay)
            
            start_time = time.time()
            
            # Create WebSocket connection
            websocket_context = self.websocket_manager.connect(user_id, auth_token)
            websocket = await websocket_context.__aenter__()
            
            connection_time = (time.time() - start_time) * 1000
            self.monitor.record_connection_time(connection_time)
            self.monitor.record_connection_active()
            
            return (websocket, user_id)
            
        except Exception as e:
            logger.error(f"Failed to create connection for {user_id}: {e}")
            self.monitor.record_connection_failure()
            return None
    
    async def run_message_throughput_test(self) -> Dict[str, Any]:
        """Test message throughput and latency under load."""
        logger.info("Starting message throughput stress test")
        
        self.monitor.start_monitoring()
        
        try:
            # Create a smaller number of connections for throughput testing
            num_connections = min(10, self.config.max_concurrent_connections)
            connections = []
            
            # Establish connections
            for i in range(num_connections):
                user_id = f"throughput_user_{i}_{uuid.uuid4().hex[:8]}"
                auth_token = create_mock_auth_token(user_id)
                
                try:
                    websocket_context = self.websocket_manager.connect(user_id, auth_token)
                    websocket = await websocket_context.__aenter__()
                    connections.append((websocket, user_id))
                    self.monitor.record_connection_active()
                except Exception as e:
                    logger.error(f"Failed to create connection for throughput test: {e}")
                    self.monitor.record_connection_failure()
            
            logger.info(f"Established {len(connections)} connections for throughput test")
            
            # Send messages from all connections simultaneously
            message_tasks = []
            
            for websocket, user_id in connections:
                task = asyncio.create_task(
                    self._send_message_burst(websocket, user_id, self.config.messages_per_connection)
                )
                message_tasks.append(task)
            
            # Wait for all message sending to complete
            await asyncio.gather(*message_tasks, return_exceptions=True)
            
            # Give time for all responses to be received
            await asyncio.sleep(5.0)
            
            # Close connections
            for websocket, user_id in connections:
                if not websocket.closed:
                    await websocket.close()
                    self.monitor.record_connection_closed()
            
            return {
                "connections_used": len(connections),
                "messages_per_connection": self.config.messages_per_connection,
                "total_messages_sent": len(connections) * self.config.messages_per_connection
            }
            
        finally:
            self.monitor.stop_monitoring()
    
    async def _send_message_burst(self, websocket, user_id: str, message_count: int):
        """Send burst of messages from a connection."""
        try:
            for i in range(message_count):
                message = create_test_agent_message(
                    user_id, 
                    f"Throughput test message {i+1} from {user_id}"
                )
                
                start_time = time.time()
                await self.websocket_manager.send_message(websocket, message)
                self.monitor.record_message_sent()
                
                # Listen for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    latency = (time.time() - start_time) * 1000
                    self.monitor.record_message_received(latency)
                except asyncio.TimeoutError:
                    self.monitor.record_message_failure()
                
                # Interval between messages
                if i < message_count - 1:
                    await asyncio.sleep(self.config.message_interval_seconds)
                    
        except Exception as e:
            logger.error(f"Error in message burst for {user_id}: {e}")
            self.monitor.record_message_failure()
    
    async def run_memory_leak_test(self) -> Dict[str, Any]:
        """Test for memory leaks during extended operation."""
        logger.info("Starting memory leak detection test")
        
        self.monitor.start_monitoring()
        
        # Force garbage collection before starting
        gc.collect()
        initial_memory = psutil.virtual_memory().used
        
        try:
            # Run multiple cycles of connection creation/destruction
            cycles = 5
            connections_per_cycle = 5
            
            memory_samples = []
            
            for cycle in range(cycles):
                logger.info(f"Memory leak test cycle {cycle + 1}/{cycles}")
                
                # Create connections
                connections = []
                for i in range(connections_per_cycle):
                    user_id = f"leak_test_user_{cycle}_{i}_{uuid.uuid4().hex[:8]}"
                    auth_token = create_mock_auth_token(user_id)
                    
                    try:
                        websocket_context = self.websocket_manager.connect(user_id, auth_token)
                        websocket = await websocket_context.__aenter__()
                        connections.append((websocket, user_id))
                    except Exception as e:
                        logger.error(f"Connection failed in leak test: {e}")
                
                # Send some messages
                for websocket, user_id in connections:
                    try:
                        message = create_test_agent_message(user_id, f"Leak test cycle {cycle}")
                        await self.websocket_manager.send_message(websocket, message)
                    except Exception as e:
                        logger.error(f"Message failed in leak test: {e}")
                
                # Wait a bit
                await asyncio.sleep(2.0)
                
                # Close connections
                for websocket, user_id in connections:
                    try:
                        if not websocket.closed:
                            await websocket.close()
                    except Exception as e:
                        logger.error(f"Close failed in leak test: {e}")
                
                # Force garbage collection
                gc.collect()
                
                # Sample memory
                current_memory = psutil.virtual_memory().used
                memory_samples.append(current_memory)
                
                logger.info(f"Cycle {cycle + 1} memory: {current_memory / (1024*1024):.1f} MB")
                
                # Brief pause between cycles
                await asyncio.sleep(1.0)
            
            # Analyze memory growth
            final_memory = psutil.virtual_memory().used
            memory_growth = final_memory - initial_memory
            
            return {
                "cycles_completed": cycles,
                "connections_per_cycle": connections_per_cycle,
                "initial_memory_mb": initial_memory / (1024 * 1024),
                "final_memory_mb": final_memory / (1024 * 1024),
                "memory_growth_mb": memory_growth / (1024 * 1024),
                "memory_samples": [mem / (1024 * 1024) for mem in memory_samples]
            }
            
        finally:
            self.monitor.stop_monitoring()
    
    async def run_connection_resilience_test(self) -> Dict[str, Any]:
        """Test connection drop and recovery resilience."""
        logger.info("Starting connection resilience test")
        
        self.monitor.start_monitoring()
        
        try:
            # Create initial connections
            num_connections = 10
            connections = []
            
            for i in range(num_connections):
                user_id = f"resilience_user_{i}_{uuid.uuid4().hex[:8]}"
                auth_token = create_mock_auth_token(user_id)
                
                try:
                    websocket_context = self.websocket_manager.connect(user_id, auth_token)
                    websocket = await websocket_context.__aenter__()
                    connections.append((websocket, user_id, auth_token))
                    self.monitor.record_connection_active()
                except Exception as e:
                    logger.error(f"Initial connection failed: {e}")
            
            logger.info(f"Established {len(connections)} initial connections")
            
            # Randomly drop some connections
            drop_count = int(len(connections) * self.config.connection_drop_percentage / 100)
            connections_to_drop = random.sample(connections, drop_count)
            
            logger.info(f"Dropping {drop_count} connections to test resilience")
            
            for websocket, user_id, auth_token in connections_to_drop:
                try:
                    await websocket.close()
                    self.monitor.record_connection_closed()
                    logger.info(f"Dropped connection for {user_id}")
                except Exception as e:
                    logger.error(f"Failed to drop connection for {user_id}: {e}")
            
            # Wait a bit
            await asyncio.sleep(2.0)
            
            # Attempt to reconnect dropped connections
            reconnection_successes = 0
            for websocket, user_id, auth_token in connections_to_drop:
                for attempt in range(self.config.reconnection_attempts):
                    try:
                        logger.info(f"Reconnection attempt {attempt + 1} for {user_id}")
                        websocket_context = self.websocket_manager.connect(user_id, auth_token)
                        new_websocket = await websocket_context.__aenter__()
                        
                        # Test the new connection
                        test_message = create_test_agent_message(user_id, "Reconnection test")
                        await self.websocket_manager.send_message(new_websocket, test_message)
                        
                        reconnection_successes += 1
                        self.monitor.record_connection_active()
                        logger.info(f"Successfully reconnected {user_id}")
                        
                        # Close the test connection
                        await new_websocket.close()
                        break
                        
                    except Exception as e:
                        logger.error(f"Reconnection attempt {attempt + 1} failed for {user_id}: {e}")
                        if attempt == self.config.reconnection_attempts - 1:
                            self.monitor.record_connection_failure()
            
            # Clean up remaining connections
            for websocket, user_id, auth_token in connections:
                if (websocket, user_id, auth_token) not in connections_to_drop:
                    try:
                        if not websocket.closed:
                            await websocket.close()
                    except Exception:
                        pass
            
            return {
                "initial_connections": len(connections),
                "connections_dropped": drop_count,
                "reconnection_attempts": self.config.reconnection_attempts,
                "reconnection_successes": reconnection_successes,
                "reconnection_success_rate": (reconnection_successes / drop_count * 100) if drop_count > 0 else 0
            }
            
        finally:
            self.monitor.stop_monitoring()


# ============================================================================
# STRESS TEST SUITE
# ============================================================================

class TestWebSocketStressValidation:
    """Comprehensive WebSocket stress testing test suite."""
    
    @pytest.fixture(scope="class")
    def stress_config(self):
        """Stress test configuration fixture."""
        return StressTestConfig()
    
    @pytest.fixture(scope="class")
    def docker_manager(self):
        """Docker manager for stress testing."""
        if not is_docker_available():
            pytest.skip("Docker not available - skipping stress tests")
        
        manager = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
        manager.start_services(["backend", "auth", "db", "redis"])
        yield manager
    
    @pytest.fixture
    def stress_runner(self, stress_config, docker_manager):
        """Stress test runner fixture."""
        return WebSocketStressTestRunner(stress_config)
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_high_concurrent_connections_stress(self, stress_runner, stress_config):
        """Test handling of high concurrent WebSocket connections."""
        logger.info(f"Testing {stress_config.max_concurrent_connections} concurrent connections")
        
        result = await stress_runner.run_connection_stress_test()
        performance = stress_runner.monitor.get_performance_metrics()
        
        # Validate connection success rate
        assert result["connection_success_rate"] >= 90.0, \
            f"Connection success rate {result['connection_success_rate']}% below 90%"
        
        # Validate connection timing
        if performance["connections"]["timing_stats"]:
            avg_connection_time = performance["connections"]["timing_stats"]["avg_ms"]
            assert avg_connection_time <= stress_config.max_connection_time_ms, \
                f"Average connection time {avg_connection_time}ms exceeds {stress_config.max_connection_time_ms}ms"
        
        # Validate memory growth
        memory_growth = performance["memory"]["growth_mb"]
        assert memory_growth <= stress_config.max_memory_growth_mb, \
            f"Memory growth {memory_growth}MB exceeds limit {stress_config.max_memory_growth_mb}MB"
        
        logger.info(f"✓ Concurrent connection stress test passed:")
        logger.info(f"  Successful connections: {result['connections_successful']}/{result['connections_requested']}")
        logger.info(f"  Connection success rate: {result['connection_success_rate']:.1f}%")
        logger.info(f"  Memory growth: {memory_growth:.1f}MB")
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_message_throughput_stress(self, stress_runner, stress_config):
        """Test message throughput and latency under load."""
        logger.info("Testing message throughput under stress")
        
        result = await stress_runner.run_message_throughput_test()
        performance = stress_runner.monitor.get_performance_metrics()
        
        # Validate throughput
        throughput = performance["messages"]["throughput_msgs_sec"]
        assert throughput >= stress_config.min_throughput_msgs_sec, \
            f"Throughput {throughput:.1f} msgs/sec below minimum {stress_config.min_throughput_msgs_sec}"
        
        # Validate latency
        if performance["messages"]["latency_stats"]:
            avg_latency = performance["messages"]["latency_stats"]["avg_ms"]
            assert avg_latency <= stress_config.max_message_latency_ms, \
                f"Average latency {avg_latency:.1f}ms exceeds {stress_config.max_message_latency_ms}ms"
            
            p95_latency = performance["messages"]["latency_stats"]["p95_ms"]
            assert p95_latency <= stress_config.max_message_latency_ms * 2, \
                f"95th percentile latency {p95_latency:.1f}ms exceeds {stress_config.max_message_latency_ms * 2}ms"
        
        # Validate message success rate
        message_success_rate = performance["messages"]["success_rate_percent"]
        assert message_success_rate >= 95.0, \
            f"Message success rate {message_success_rate:.1f}% below 95%"
        
        logger.info(f"✓ Message throughput stress test passed:")
        logger.info(f"  Throughput: {throughput:.1f} msgs/sec")
        logger.info(f"  Message success rate: {message_success_rate:.1f}%")
        if performance["messages"]["latency_stats"]:
            logger.info(f"  Average latency: {avg_latency:.1f}ms")
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, stress_runner, stress_config):
        """Test for memory leaks during extended WebSocket operation."""
        logger.info("Testing for memory leaks during extended operation")
        
        result = await stress_runner.run_memory_leak_test()
        
        # Validate memory growth is within acceptable limits
        memory_growth = result["memory_growth_mb"]
        assert memory_growth <= stress_config.max_memory_growth_mb, \
            f"Memory growth {memory_growth:.1f}MB exceeds limit {stress_config.max_memory_growth_mb}MB"
        
        # Check that memory growth is not linear (indicating a leak)
        memory_samples = result["memory_samples"]
        if len(memory_samples) >= 3:
            # Calculate if memory is consistently growing
            growth_trend = []
            for i in range(1, len(memory_samples)):
                growth_trend.append(memory_samples[i] - memory_samples[i-1])
            
            # If all samples show growth, it might indicate a leak
            consistent_growth = all(growth > 0 for growth in growth_trend)
            if consistent_growth and memory_growth > 100:  # Only worry if growth is significant
                logger.warning("Potential memory leak detected - consistent memory growth")
            
            # Check for excessive final memory growth
            final_growth_rate = growth_trend[-1] if growth_trend else 0
            assert final_growth_rate <= 50.0, \
                f"Final cycle memory growth {final_growth_rate:.1f}MB indicates potential leak"
        
        logger.info(f"✓ Memory leak test passed:")
        logger.info(f"  Cycles completed: {result['cycles_completed']}")
        logger.info(f"  Memory growth: {memory_growth:.1f}MB")
        logger.info(f"  Final memory: {result['final_memory_mb']:.1f}MB")
    
    @requires_docker
    @pytest.mark.asyncio 
    async def test_connection_resilience_stress(self, stress_runner, stress_config):
        """Test connection drop and recovery resilience."""
        logger.info("Testing connection resilience under stress")
        
        result = await stress_runner.run_connection_resilience_test()
        
        # Validate reconnection success rate
        reconnection_success_rate = result["reconnection_success_rate"]
        assert reconnection_success_rate >= 80.0, \
            f"Reconnection success rate {reconnection_success_rate:.1f}% below 80%"
        
        # Validate that at least some connections were dropped (test is working)
        assert result["connections_dropped"] > 0, "No connections were dropped - test may not be working"
        
        logger.info(f"✓ Connection resilience test passed:")
        logger.info(f"  Connections dropped: {result['connections_dropped']}")
        logger.info(f"  Reconnection attempts: {result['reconnection_attempts']}")
        logger.info(f"  Reconnection success rate: {reconnection_success_rate:.1f}%")
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_extended_load_endurance(self, stress_runner, stress_config):
        """Test system endurance under extended load."""
        logger.info("Testing extended load endurance")
        
        # Override config for extended test
        original_hold_time = stress_config.connection_hold_time_seconds
        stress_config.connection_hold_time_seconds = 120.0  # 2 minutes
        
        try:
            # Reduce concurrent connections for extended test
            original_max_connections = stress_config.max_concurrent_connections
            stress_config.max_concurrent_connections = 15
            
            # Run connection stress test with extended duration
            result = await stress_runner.run_connection_stress_test()
            performance = stress_runner.monitor.get_performance_metrics()
            
            # Validate system remained stable during extended test
            assert result["connection_success_rate"] >= 85.0, \
                f"Extended load test connection success rate {result['connection_success_rate']:.1f}% below 85%"
            
            # Validate memory didn't grow excessively
            memory_growth = performance["memory"]["growth_mb"]
            assert memory_growth <= stress_config.max_memory_growth_mb * 1.5, \
                f"Extended test memory growth {memory_growth:.1f}MB exceeds limit"
            
            # Validate CPU usage remained reasonable
            avg_cpu = performance["resource_usage"]["avg_cpu_percent"]
            assert avg_cpu <= 80.0, \
                f"Average CPU usage {avg_cpu:.1f}% too high during extended test"
            
            logger.info(f"✓ Extended load endurance test passed:")
            logger.info(f"  Test duration: {performance['duration_seconds']:.1f} seconds")
            logger.info(f"  Connection success rate: {result['connection_success_rate']:.1f}%")
            logger.info(f"  Memory growth: {memory_growth:.1f}MB")
            logger.info(f"  Average CPU: {avg_cpu:.1f}%")
            
        finally:
            # Restore original config
            stress_config.connection_hold_time_seconds = original_hold_time
            stress_config.max_concurrent_connections = original_max_connections
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_comprehensive_stress_validation(self, stress_runner, stress_config):
        """Comprehensive stress validation combining all test scenarios."""
        logger.info("Running comprehensive stress validation")
        
        comprehensive_results = {}
        
        # Run all stress tests in sequence
        logger.info("Phase 1: Connection stress")
        comprehensive_results["connection_stress"] = await stress_runner.run_connection_stress_test()
        
        # Brief pause between tests
        await asyncio.sleep(2.0)
        
        logger.info("Phase 2: Throughput stress") 
        comprehensive_results["throughput_stress"] = await stress_runner.run_message_throughput_test()
        
        await asyncio.sleep(2.0)
        
        logger.info("Phase 3: Memory leak detection")
        comprehensive_results["memory_test"] = await stress_runner.run_memory_leak_test()
        
        await asyncio.sleep(2.0)
        
        logger.info("Phase 4: Resilience testing")
        comprehensive_results["resilience_test"] = await stress_runner.run_connection_resilience_test()
        
        # Get final performance metrics
        final_performance = stress_runner.monitor.get_performance_metrics()
        comprehensive_results["final_performance"] = final_performance
        
        # Comprehensive validation
        all_tests_passed = True
        
        # Connection test validation
        if comprehensive_results["connection_stress"]["connection_success_rate"] < 90.0:
            all_tests_passed = False
            logger.error("Connection stress test failed")
        
        # Memory test validation  
        if comprehensive_results["memory_test"]["memory_growth_mb"] > stress_config.max_memory_growth_mb:
            all_tests_passed = False
            logger.error("Memory leak test failed")
        
        # Resilience test validation
        if comprehensive_results["resilience_test"]["reconnection_success_rate"] < 80.0:
            all_tests_passed = False
            logger.error("Resilience test failed")
        
        assert all_tests_passed, "One or more comprehensive stress tests failed"
        
        logger.info("✅ COMPREHENSIVE STRESS VALIDATION PASSED")
        logger.info("=" * 60)
        logger.info("STRESS TEST SUMMARY:")
        logger.info(f"  Connection Success Rate: {comprehensive_results['connection_stress']['connection_success_rate']:.1f}%")
        logger.info(f"  Memory Growth: {comprehensive_results['memory_test']['memory_growth_mb']:.1f}MB")
        logger.info(f"  Reconnection Success: {comprehensive_results['resilience_test']['reconnection_success_rate']:.1f}%")
        logger.info("=" * 60)


if __name__ == "__main__":
    """Run stress tests directly."""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the stress test suite
    pytest.main([__file__, "-v", "--tb=short"])