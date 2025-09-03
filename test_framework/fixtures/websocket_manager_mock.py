#!/usr/bin/env python
"""
Canonical WebSocket Manager Mock - Consolidation of 67+ MockWebSocketManager implementations

This unified mock replaces all individual MockWebSocketManager implementations across the codebase.
It provides configurable behavior for all testing scenarios while maintaining compatibility.

Business Value: Reduces test maintenance overhead and ensures consistent WebSocket testing patterns.
"""

import asyncio
import json
import time
import threading
import uuid
import random
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Set, Any, Optional, Callable, Union, Tuple
from unittest.mock import AsyncMock, MagicMock


class MockWebSocketState(str, Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class MockBehaviorMode(str, Enum):
    """Mock behavior modes for different test scenarios."""
    NORMAL = "normal"  # Standard successful behavior
    NETWORK_PARTITION = "network_partition"  # Simulates network issues
    SLOW_NETWORK = "slow_network"  # Simulates latency
    PACKET_LOSS = "packet_loss"  # Simulates packet loss
    MEMORY_PRESSURE = "memory_pressure"  # Simulates resource constraints
    CONNECTION_LIMIT = "connection_limit"  # Simulates connection limits
    MALFORMED_DATA = "malformed_data"  # Simulates data corruption
    TIMEOUT_PRONE = "timeout_prone"  # Simulates timeouts
    AUTHENTICATION_FAILURE = "auth_failure"  # Simulates auth issues
    RACE_CONDITIONS = "race_conditions"  # Simulates concurrency issues


@dataclass
class MockConfiguration:
    """Configuration for mock behavior."""
    mode: MockBehaviorMode = MockBehaviorMode.NORMAL
    
    # Network simulation
    latency_ms: float = 0  # Network latency in milliseconds
    packet_loss_rate: float = 0.0  # Packet loss rate (0.0-1.0)
    bandwidth_limit: Optional[int] = None  # Bytes per second
    
    # Resource limits
    memory_limit: int = 1024 * 1024  # 1MB default
    connection_limit: int = 100
    message_queue_size: int = 1000
    
    # Failure simulation
    failure_rate: float = 0.0  # General failure rate (0.0-1.0)
    timeout_probability: float = 0.0  # Timeout probability (0.0-1.0)
    should_authenticate: bool = True
    auth_failure_rate: float = 0.0
    
    # Performance testing
    enable_metrics: bool = True
    track_timing: bool = True
    track_memory: bool = True
    
    # Compliance testing
    enforce_event_order: bool = False
    validate_message_format: bool = True
    strict_threading: bool = False


@dataclass
class WebSocketMetrics:
    """Metrics collection for WebSocket operations."""
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    connections_made: int = 0
    connections_dropped: int = 0
    errors_count: int = 0
    timeouts_count: int = 0
    average_latency: float = 0.0
    max_latency: float = 0.0
    memory_usage: int = 0
    start_time: float = field(default_factory=time.time)
    
    def get_uptime(self) -> float:
        """Get uptime in seconds."""
        return time.time() - self.start_time
    
    def calculate_throughput(self) -> Dict[str, float]:
        """Calculate throughput metrics."""
        uptime = self.get_uptime()
        if uptime == 0:
            return {"messages_per_second": 0.0, "bytes_per_second": 0.0}
        
        return {
            "messages_per_second": (self.messages_sent + self.messages_received) / uptime,
            "bytes_per_second": (self.bytes_sent + self.bytes_received) / uptime
        }


class MockWebSocketManager:
    """
    Unified MockWebSocketManager that supports all testing scenarios.
    
    This mock consolidates 67+ individual implementations into a single,
    configurable mock that can handle:
    - All WebSocket event types (agent_started, agent_thinking, etc.)
    - Network simulation (latency, packet loss, partitions)
    - Resource constraints (memory, connections)
    - Error conditions (timeouts, auth failures, malformed data)
    - Performance testing (metrics, timing, throughput)
    - Compliance validation (event order, message format)
    - Concurrency scenarios (race conditions, threading)
    """
    
    def __init__(self, config: Optional[MockConfiguration] = None):
        """Initialize the mock with optional configuration."""
        self.config = config or MockConfiguration()
        
        # Message tracking
        self.messages: List[Dict] = []
        self.event_timeline: List[Tuple[float, str, Dict]] = []  # (timestamp, event_type, data)
        self.message_queues: Dict[str, deque] = defaultdict(deque)
        
        # Connection tracking
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.user_connections: Dict[str, List[str]] = defaultdict(list)
        self.connection_states: Dict[str, MockWebSocketState] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        self._send_lock = asyncio.Lock() if not self.config.strict_threading else threading.Lock()
        
        # Metrics and monitoring
        self.metrics = WebSocketMetrics() if self.config.enable_metrics else None
        self.call_history: List[Dict] = []
        
        # Failure simulation state
        self.partition_active = False
        self.failed_sends: List[str] = []
        self.timeout_events: List[Dict] = []
        self.auth_failures: List[Dict] = []
        
        # Performance testing state
        self.concurrent_operations = 0
        self.max_concurrent = 0
        self.operation_times: List[float] = []
        
        # Compliance tracking
        self.required_events = {"agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"}
        self.event_compliance: Dict[str, Set[str]] = defaultdict(set)
        
        # Advanced simulation state
        self.memory_usage = 0
        self.active_timeouts: Dict[str, float] = {}  # operation_id -> timeout_time
        self.race_condition_tracker: Dict[str, List] = defaultdict(list)
        
        # Initialize behavior-specific state
        self._initialize_behavior_state()
    
    def _initialize_behavior_state(self):
        """Initialize state based on behavior mode."""
        if self.config.mode == MockBehaviorMode.NETWORK_PARTITION:
            self.partition_recovery_queue: List[Tuple] = []
        elif self.config.mode == MockBehaviorMode.SLOW_NETWORK:
            self.send_times: List[float] = []
        elif self.config.mode == MockBehaviorMode.PACKET_LOSS:
            self.lost_packets: List[str] = []
            self.retry_attempts: List[Dict] = []
        elif self.config.mode == MockBehaviorMode.MEMORY_PRESSURE:
            self.memory_pressure_events: List[Dict] = []
            self.garbage_collections = 0
        elif self.config.mode == MockBehaviorMode.RACE_CONDITIONS:
            self.context_switches = 0
            self.current_context = None
    
    @classmethod
    def create_for_scenario(cls, scenario: str, **kwargs) -> 'MockWebSocketManager':
        """
        Factory method to create mock for specific test scenarios.
        
        Common scenarios:
        - "basic": Standard mock for simple tests
        - "compliance": Event compliance validation
        - "performance": Performance and throughput testing
        - "resilience": Network failure simulation
        - "concurrency": Multi-threading and race condition testing
        - "resource_limits": Memory and connection limit testing
        """
        if scenario == "basic":
            config = MockConfiguration(mode=MockBehaviorMode.NORMAL)
        elif scenario == "compliance":
            config = MockConfiguration(
                mode=MockBehaviorMode.NORMAL,
                enforce_event_order=True,
                validate_message_format=True
            )
        elif scenario == "performance":
            config = MockConfiguration(
                mode=MockBehaviorMode.NORMAL,
                enable_metrics=True,
                track_timing=True,
                track_memory=True
            )
        elif scenario == "resilience":
            config = MockConfiguration(
                mode=MockBehaviorMode.NETWORK_PARTITION,
                packet_loss_rate=0.1,
                timeout_probability=0.2,
                failure_rate=0.15
            )
        elif scenario == "slow_network":
            config = MockConfiguration(
                mode=MockBehaviorMode.SLOW_NETWORK,
                latency_ms=200,
                bandwidth_limit=1024 * 50  # 50KB/s
            )
        elif scenario == "concurrency":
            config = MockConfiguration(
                mode=MockBehaviorMode.RACE_CONDITIONS,
                strict_threading=True
            )
        elif scenario == "resource_limits":
            config = MockConfiguration(
                mode=MockBehaviorMode.MEMORY_PRESSURE,
                memory_limit=512 * 1024,  # 512KB
                connection_limit=10,
                message_queue_size=50
            )
        elif scenario == "auth_testing":
            config = MockConfiguration(
                mode=MockBehaviorMode.AUTHENTICATION_FAILURE,
                auth_failure_rate=0.3
            )
        else:
            config = MockConfiguration(**kwargs)
        
        return cls(config)
    
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """
        Send message to a thread with full behavior simulation.
        
        This is the core method that all tests rely on. It handles:
        - Message validation and tracking
        - Behavior mode simulation
        - Metrics collection
        - Event compliance checking
        """
        operation_start = time.time()
        
        try:
            # Pre-send validation
            if not await self._validate_send_operation(thread_id, message):
                return False
            
            # Apply behavior mode effects
            if not await self._apply_behavior_mode(thread_id, message):
                return False
            
            # Record the message
            await self._record_message(thread_id, message)
            
            # Update metrics
            if self.metrics:
                self.metrics.messages_sent += 1
                self.metrics.bytes_sent += len(json.dumps(message, default=str))
                
                operation_time = time.time() - operation_start
                self.operation_times.append(operation_time)
                self.metrics.max_latency = max(self.metrics.max_latency, operation_time)
                
                if self.operation_times:
                    self.metrics.average_latency = sum(self.operation_times) / len(self.operation_times)
            
            return True
            
        except Exception as e:
            await self._handle_send_error(thread_id, message, str(e))
            return False
    
    async def _validate_send_operation(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Validate send operation based on configuration."""
        # Message format validation
        if self.config.validate_message_format:
            if not message.get('type'):
                if self.metrics:
                    self.metrics.errors_count += 1
                return False
            
            # Check for oversized messages
            message_size = len(json.dumps(message, default=str))
            if message_size > 1024 * 1024:  # 1MB limit
                if self.metrics:
                    self.metrics.errors_count += 1
                return False
        
        # Connection limit check
        if len(self.connections) >= self.config.connection_limit:
            if self.metrics:
                self.metrics.errors_count += 1
            return False
        
        # Memory limit check
        if self.config.track_memory and self.memory_usage > self.config.memory_limit:
            self.memory_usage = 0  # Simulate garbage collection
            if self.metrics:
                self.metrics.memory_usage = 0
            return len(json.dumps(message, default=str)) < self.config.memory_limit
        
        return True
    
    async def _apply_behavior_mode(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Apply behavior mode specific effects."""
        if self.config.mode == MockBehaviorMode.NETWORK_PARTITION:
            return await self._simulate_network_partition(thread_id, message)
        elif self.config.mode == MockBehaviorMode.SLOW_NETWORK:
            return await self._simulate_slow_network(thread_id, message)
        elif self.config.mode == MockBehaviorMode.PACKET_LOSS:
            return await self._simulate_packet_loss(thread_id, message)
        elif self.config.mode == MockBehaviorMode.TIMEOUT_PRONE:
            return await self._simulate_timeouts(thread_id, message)
        elif self.config.mode == MockBehaviorMode.AUTHENTICATION_FAILURE:
            return await self._simulate_auth_failure(thread_id, message)
        elif self.config.mode == MockBehaviorMode.RACE_CONDITIONS:
            return await self._simulate_race_conditions(thread_id, message)
        
        # Apply general failure rate
        if random.random() < self.config.failure_rate:
            self.failed_sends.append(message.get('type', 'unknown'))
            return False
        
        # Apply network latency
        if self.config.latency_ms > 0:
            await asyncio.sleep(self.config.latency_ms / 1000.0)
        
        return True
    
    async def _simulate_network_partition(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Simulate network partition behavior."""
        if self.partition_active:
            self.partition_recovery_queue.append((thread_id, message))
            self.failed_sends.append(message.get('type', 'unknown'))
            return False
        
        # Random partition activation
        if random.random() < 0.1:  # 10% chance of partition
            self.partition_active = True
            # Schedule recovery
            asyncio.create_task(self._recover_from_partition())
        
        return True
    
    async def _recover_from_partition(self):
        """Simulate recovery from network partition."""
        await asyncio.sleep(random.uniform(1.0, 3.0))  # Recovery time
        self.partition_active = False
        
        # Process queued messages
        while self.partition_recovery_queue:
            thread_id, message = self.partition_recovery_queue.pop(0)
            await self._record_message(thread_id, message)
    
    async def _simulate_slow_network(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Simulate slow network conditions."""
        latency = self.config.latency_ms / 1000.0
        
        # Add random jitter
        jitter = random.uniform(0, latency * 0.5)
        total_delay = latency + jitter
        
        await asyncio.sleep(total_delay)
        self.send_times.append(total_delay)
        
        return True
    
    async def _simulate_packet_loss(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Simulate packet loss with retry logic."""
        if random.random() < self.config.packet_loss_rate:
            self.lost_packets.append(message.get('type', 'unknown'))
            
            # Simulate retry
            retry_attempt = {
                'thread_id': thread_id,
                'message_type': message.get('type', 'unknown'),
                'timestamp': time.time()
            }
            self.retry_attempts.append(retry_attempt)
            
            # Retry after delay
            await asyncio.sleep(0.1)
            if random.random() < 0.7:  # 70% retry success rate
                return True
            else:
                return False
        
        return True
    
    async def _simulate_timeouts(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Simulate timeout conditions."""
        if random.random() < self.config.timeout_probability:
            operation_id = f"{thread_id}_{message.get('type')}_{time.time()}"
            
            timeout_event = {
                'thread_id': thread_id,
                'message_type': message.get('type', 'unknown'),
                'timestamp': time.time(),
                'operation_id': operation_id
            }
            self.timeout_events.append(timeout_event)
            
            if self.metrics:
                self.metrics.timeouts_count += 1
            
            # Simulate timeout delay
            await asyncio.sleep(random.uniform(5.0, 10.0))
            return False
        
        return True
    
    async def _simulate_auth_failure(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Simulate authentication failures."""
        if random.random() < self.config.auth_failure_rate:
            auth_failure = {
                'thread_id': thread_id,
                'message_type': message.get('type', 'unknown'),
                'timestamp': time.time(),
                'error': 'Authentication failed'
            }
            self.auth_failures.append(auth_failure)
            return False
        
        return True
    
    async def _simulate_race_conditions(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """Simulate race condition scenarios."""
        # Track context switches
        if self.current_context != thread_id:
            self.context_switches += 1
            self.current_context = thread_id
        
        # Add artificial race condition potential
        event_type = message.get('type', 'unknown')
        timestamp = time.time()
        
        self.race_condition_tracker[thread_id].append((timestamp, event_type))
        
        # Detect potential race conditions
        if len(self.race_condition_tracker[thread_id]) > 1:
            events = self.race_condition_tracker[thread_id]
            if len(events) >= 2:
                time_diff = events[-1][0] - events[-2][0]
                if time_diff < 0.001:  # Events within 1ms could race
                    # Introduce small delay to simulate race resolution
                    await asyncio.sleep(random.uniform(0.001, 0.005))
        
        return True
    
    async def _record_message(self, thread_id: str, message: Dict[str, Any]):
        """Record message with full tracking."""
        timestamp = time.time()
        event_type = message.get('type', 'unknown')
        
        # Use appropriate locking based on configuration
        if self.config.strict_threading:
            with self._lock:
                self._do_record_message(thread_id, message, timestamp, event_type)
        else:
            async with self._send_lock:
                self._do_record_message(thread_id, message, timestamp, event_type)
    
    def _do_record_message(self, thread_id: str, message: Dict[str, Any], timestamp: float, event_type: str):
        """Internal message recording (thread-safe)."""
        event_record = {
            'thread_id': thread_id,
            'message': message,
            'event_type': event_type,
            'timestamp': timestamp,
            'sequence': len(self.messages)
        }
        
        self.messages.append(event_record)
        self.event_timeline.append((timestamp, event_type, message))
        
        # Track event compliance
        self.event_compliance[thread_id].add(event_type)
        
        # Update memory usage estimate
        if self.config.track_memory:
            message_size = len(json.dumps(message, default=str))
            self.memory_usage += message_size
            if self.metrics:
                self.metrics.memory_usage = self.memory_usage
        
        # Add to thread-specific queue
        if len(self.message_queues[thread_id]) >= self.config.message_queue_size:
            self.message_queues[thread_id].popleft()  # Remove oldest
        self.message_queues[thread_id].append(event_record)
    
    async def _handle_send_error(self, thread_id: str, message: Dict[str, Any], error: str):
        """Handle send operation errors."""
        if self.metrics:
            self.metrics.errors_count += 1
        
        error_record = {
            'thread_id': thread_id,
            'message_type': message.get('type', 'unknown'),
            'error': error,
            'timestamp': time.time()
        }
        
        # Store error for analysis
        if not hasattr(self, 'errors'):
            self.errors = []
        self.errors.append(error_record)
    
    # Connection management methods
    async def connect_user(self, user_id: str, websocket, thread_id: str):
        """Mock user connection with full state tracking."""
        if self.metrics:
            self.metrics.connections_made += 1
        
        connection_info = {
            'user_id': user_id,
            'connected': True,
            'websocket': websocket,
            'connected_at': time.time(),
            'state': MockWebSocketState.CONNECTED
        }
        
        self.connections[thread_id] = connection_info
        self.user_connections[user_id].append(thread_id)
        self.connection_states[thread_id] = MockWebSocketState.CONNECTED
    
    async def disconnect_user(self, user_id: str, websocket, thread_id: str):
        """Mock user disconnection with cleanup."""
        if thread_id in self.connections:
            self.connections[thread_id]['connected'] = False
            self.connections[thread_id]['disconnected_at'] = time.time()
            self.connection_states[thread_id] = MockWebSocketState.DISCONNECTED
            
            if self.metrics:
                self.metrics.connections_dropped += 1
        
        if user_id in self.user_connections:
            if thread_id in self.user_connections[user_id]:
                self.user_connections[user_id].remove(thread_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
    
    # Query and analysis methods
    def get_events_for_thread(self, thread_id: str) -> List[Dict]:
        """Get all events for a specific thread in chronological order."""
        return [msg for msg in self.messages if msg['thread_id'] == thread_id]
    
    def get_required_event_compliance(self, thread_id: str) -> Dict[str, bool]:
        """Check for all 5 REQUIRED WebSocket events for business value."""
        events = self.event_compliance[thread_id]
        return {event: event in events for event in self.required_events}
    
    def get_compliance_score(self, thread_id: str) -> float:
        """Calculate compliance score (0.0-1.0) for required events."""
        compliance = self.get_required_event_compliance(thread_id)
        completed_events = sum(1 for passed in compliance.values() if passed)
        return completed_events / len(self.required_events)
    
    def get_all_compliance_scores(self) -> Dict[str, float]:
        """Get compliance scores for all threads."""
        return {
            thread_id: self.get_compliance_score(thread_id)
            for thread_id in self.event_compliance.keys()
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        if not self.metrics:
            return {}
        
        throughput = self.metrics.calculate_throughput()
        
        return {
            'messages_sent': self.metrics.messages_sent,
            'messages_received': self.metrics.messages_received,
            'bytes_sent': self.metrics.bytes_sent,
            'bytes_received': self.metrics.bytes_received,
            'connections_made': self.metrics.connections_made,
            'connections_dropped': self.metrics.connections_dropped,
            'errors_count': self.metrics.errors_count,
            'timeouts_count': self.metrics.timeouts_count,
            'average_latency': self.metrics.average_latency,
            'max_latency': self.metrics.max_latency,
            'memory_usage': self.metrics.memory_usage,
            'uptime_seconds': self.metrics.get_uptime(),
            'throughput': throughput,
            'concurrent_operations': self.concurrent_operations,
            'max_concurrent': self.max_concurrent
        }
    
    def get_failure_analysis(self) -> Dict[str, Any]:
        """Get detailed failure analysis."""
        return {
            'failed_sends': len(self.failed_sends),
            'failed_send_types': list(set(self.failed_sends)),
            'timeout_events': len(self.timeout_events),
            'auth_failures': len(self.auth_failures),
            'lost_packets': len(getattr(self, 'lost_packets', [])),
            'retry_attempts': len(getattr(self, 'retry_attempts', [])),
            'partition_active': self.partition_active,
            'memory_pressure_events': len(getattr(self, 'memory_pressure_events', [])),
            'context_switches': getattr(self, 'context_switches', 0)
        }
    
    def get_network_simulation_stats(self) -> Dict[str, Any]:
        """Get network simulation statistics."""
        return {
            'mode': self.config.mode,
            'latency_ms': self.config.latency_ms,
            'packet_loss_rate': self.config.packet_loss_rate,
            'failure_rate': self.config.failure_rate,
            'timeout_probability': self.config.timeout_probability,
            'actual_send_times': getattr(self, 'send_times', []),
            'partition_recovery_queue_size': len(getattr(self, 'partition_recovery_queue', []))
        }
    
    # Utility methods
    def clear_messages(self):
        """Clear all recorded messages and reset state."""
        with self._lock if self.config.strict_threading else asyncio.Lock():
            self.messages.clear()
            self.event_timeline.clear()
            self.event_compliance.clear()
            self.failed_sends.clear()
            self.timeout_events.clear()
            self.auth_failures.clear()
            
            for queue in self.message_queues.values():
                queue.clear()
            
            if self.metrics:
                self.metrics = WebSocketMetrics()
            
            self.memory_usage = 0
            self.concurrent_operations = 0
            self.max_concurrent = 0
            self.operation_times.clear()
    
    def reset_behavior_state(self):
        """Reset behavior-specific state."""
        self.partition_active = False
        if hasattr(self, 'partition_recovery_queue'):
            self.partition_recovery_queue.clear()
        if hasattr(self, 'lost_packets'):
            self.lost_packets.clear()
        if hasattr(self, 'retry_attempts'):
            self.retry_attempts.clear()
        if hasattr(self, 'send_times'):
            self.send_times.clear()
    
    def simulate_recovery(self):
        """Manually trigger recovery from failure states."""
        self.partition_active = False
        self.failed_sends.clear()
        self.timeout_events.clear()
    
    def enable_partition(self):
        """Manually enable network partition simulation."""
        self.partition_active = True
    
    def disable_partition(self):
        """Manually disable network partition simulation."""
        self.partition_active = False
    
    # Context managers for test scenarios
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.clear_messages()
        return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        self.clear_messages()
        return False


# Convenience factory functions for common test scenarios

def create_basic_mock() -> MockWebSocketManager:
    """Create a basic mock for simple tests."""
    return MockWebSocketManager.create_for_scenario("basic")

def create_compliance_mock() -> MockWebSocketManager:
    """Create a mock for WebSocket event compliance testing."""
    return MockWebSocketManager.create_for_scenario("compliance")

def create_performance_mock() -> MockWebSocketManager:
    """Create a mock for performance testing with metrics."""
    return MockWebSocketManager.create_for_scenario("performance")

def create_resilience_mock() -> MockWebSocketManager:
    """Create a mock for network resilience testing."""
    return MockWebSocketManager.create_for_scenario("resilience")

def create_concurrency_mock() -> MockWebSocketManager:
    """Create a mock for concurrency and race condition testing."""
    return MockWebSocketManager.create_for_scenario("concurrency")

def create_resource_limits_mock() -> MockWebSocketManager:
    """Create a mock for resource limit testing."""
    return MockWebSocketManager.create_for_scenario("resource_limits")

def create_slow_network_mock(latency_ms: float = 200) -> MockWebSocketManager:
    """Create a mock with slow network simulation."""
    return MockWebSocketManager.create_for_scenario("slow_network", latency_ms=latency_ms)

def create_auth_testing_mock(failure_rate: float = 0.3) -> MockWebSocketManager:
    """Create a mock for authentication testing."""
    return MockWebSocketManager.create_for_scenario("auth_testing", auth_failure_rate=failure_rate)


# Pytest fixtures for easy integration
def pytest_mock_websocket_manager():
    """Pytest fixture for basic MockWebSocketManager."""
    return create_basic_mock()

def pytest_mock_compliance():
    """Pytest fixture for compliance testing."""
    return create_compliance_mock()

def pytest_mock_performance():
    """Pytest fixture for performance testing.""" 
    return create_performance_mock()


# Legacy compatibility - maps old mock patterns to new unified mock
class LegacyMockWebSocketManager(MockWebSocketManager):
    """
    Compatibility wrapper for legacy test code.
    
    Provides the same interface as old mocks while using the new unified implementation.
    """
    
    def __init__(self, strict_mode: bool = True, **kwargs):
        """Legacy constructor interface."""
        config = MockConfiguration(
            validate_message_format=strict_mode,
            enforce_event_order=strict_mode,
            **kwargs
        )
        super().__init__(config)
        
        # Legacy attributes for backward compatibility
        self.strict_mode = strict_mode
        self.events = self.messages  # Alias
        self.event_counts = defaultdict(int)
        self.errors = []
        self.warnings = []
        self.start_time = time.time()
    
    def record(self, event: Dict) -> None:
        """Legacy record method for compatibility."""
        thread_id = event.get('thread_id', 'legacy_thread')
        asyncio.create_task(self.send_to_thread(thread_id, event))
        
        event_type = event.get('type', 'unknown')
        self.event_counts[event_type] += 1


# Export the main class and convenience functions
__all__ = [
    'MockWebSocketManager',
    'MockConfiguration', 
    'MockBehaviorMode',
    'WebSocketMetrics',
    'create_basic_mock',
    'create_compliance_mock', 
    'create_performance_mock',
    'create_resilience_mock',
    'create_concurrency_mock',
    'create_resource_limits_mock',
    'create_slow_network_mock',
    'create_auth_testing_mock',
    'LegacyMockWebSocketManager'
]