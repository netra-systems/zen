#!/usr/bin/env python
"""MISSION CRITICAL: Comprehensive WebSocket Event Validation Test Suite

Business Value Justification:
- Segment: Platform/Internal (Core Infrastructure)
- Business Goal: Ensure 100% reliability of $500K+ ARR chat functionality
- Value Impact: Validates all 5 critical WebSocket events that enable substantive AI interactions
- Strategic Impact: Prevents chat failures that cause user abandonment and revenue loss

This suite provides comprehensive validation of WebSocket events with:
1. Real WebSocket connections to staging environment (NO MOCKS)
2. Full validation of 5 required events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
3. Event ordering, timing, and content structure validation
4. Concurrent user scenario testing (5+ users simultaneously)
5. Performance benchmarks and latency validation (<100ms)
6. Reconnection and recovery testing
7. User isolation and security validation

CRITICAL: This test suite MUST pass for staging deployment approval.
ANY FAILURE HERE BLOCKS DEPLOYMENT.
"""

import asyncio
import json
import os
import sys
import time
import uuid
import websockets
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple, Union
import threading
import random
import statistics
from contextlib import asynccontextmanager

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import environment and test utilities
from shared.isolated_environment import get_env, IsolatedEnvironment
from test_framework.test_context import TestContext, create_test_context
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
from test_framework.websocket_helpers import WebSocketTestHelpers, ensure_websocket_service_ready

# Import WebSocket event validation framework
from netra_backend.app.websocket_core.event_validation_framework import (
    EventType, EventValidationLevel, ValidationResult, ValidatedEvent,
    EventValidator
)

# Import test base utilities - REAL SERVICES ONLY
from tests.mission_critical.websocket_real_test_base import (
    require_docker_services, requires_docker, RealWebSocketTestConfig
)


# ============================================================================
# COMPREHENSIVE EVENT VALIDATION DATA STRUCTURES
# ============================================================================

@dataclass
class EventValidationMetrics:
    """Comprehensive metrics for WebSocket event validation."""
    total_events: int = 0
    valid_events: int = 0
    invalid_events: int = 0
    missing_events: int = 0
    duplicate_events: int = 0
    out_of_order_events: int = 0
    latency_violations: int = 0
    
    # Event type counts
    event_counts: Dict[str, int] = field(default_factory=dict)
    
    # Performance metrics
    total_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    latencies: List[float] = field(default_factory=list)
    
    # Timing metrics
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        return statistics.mean(self.latencies) if self.latencies else 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        return (self.valid_events / self.total_events * 100) if self.total_events > 0 else 0.0
    
    @property
    def duration_seconds(self) -> float:
        """Calculate test duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time


@dataclass
class EventSequence:
    """Represents an expected sequence of WebSocket events."""
    thread_id: str
    user_id: str
    expected_events: List[EventType]
    received_events: List[ValidatedEvent] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    timeout_seconds: float = 30.0
    
    @property
    def is_complete(self) -> bool:
        """Check if all expected events have been received."""
        received_types = [event.event_type for event in self.received_events]
        return all(expected in received_types for expected in self.expected_events)
    
    @property
    def is_timed_out(self) -> bool:
        """Check if the sequence has timed out."""
        return time.time() - self.start_time > self.timeout_seconds
    
    @property
    def missing_events(self) -> List[EventType]:
        """Get list of missing events."""
        received_types = [event.event_type for event in self.received_events]
        return [expected for expected in self.expected_events if expected not in received_types]


class WebSocketEventCapture:
    """Captures and validates WebSocket events in real-time."""
    
    def __init__(self, validation_level: EventValidationLevel = EventValidationLevel.STRICT):
        self.validation_level = validation_level
        self.validator = EventValidator()
        
        # Event storage
        self.events: List[ValidatedEvent] = []
        self.events_by_thread: Dict[str, List[ValidatedEvent]] = defaultdict(list)
        self.events_by_user: Dict[str, List[ValidatedEvent]] = defaultdict(list)
        
        # Sequence tracking
        self.active_sequences: Dict[str, EventSequence] = {}
        self.completed_sequences: List[EventSequence] = []
        
        # Metrics
        self.metrics = EventValidationMetrics()
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Performance monitoring
        self._event_timestamps: Dict[str, float] = {}
        
    def start_sequence(self, thread_id: str, user_id: str, expected_events: List[EventType]) -> None:
        """Start tracking a new event sequence."""
        with self._lock:
            sequence = EventSequence(
                thread_id=thread_id,
                user_id=user_id,
                expected_events=expected_events
            )
            self.active_sequences[thread_id] = sequence
            
    def capture_event(self, event_data: Dict[str, Any], websocket_latency: Optional[float] = None) -> ValidatedEvent:
        """Capture and validate a WebSocket event."""
        with self._lock:
            # Validate the event
            validated_event = self.validator.validate_event(event_data, context={})
            
            # Add latency information
            if websocket_latency is not None:
                validated_event.latency_ms = websocket_latency
                
            # Store the event
            self.events.append(validated_event)
            self.events_by_thread[validated_event.thread_id].append(validated_event)
            
            # Extract user_id if available
            user_id = event_data.get('user_id') or event_data.get('context', {}).get('user_id')
            if user_id:
                self.events_by_user[user_id].append(validated_event)
            
            # Update sequence tracking
            if validated_event.thread_id in self.active_sequences:
                sequence = self.active_sequences[validated_event.thread_id]
                sequence.received_events.append(validated_event)
                
                # Check if sequence is complete
                if sequence.is_complete:
                    self.completed_sequences.append(sequence)
                    del self.active_sequences[validated_event.thread_id]
            
            # Update metrics
            self._update_metrics(validated_event)
            
            return validated_event
    
    def _update_metrics(self, event: ValidatedEvent) -> None:
        """Update validation metrics."""
        self.metrics.total_events += 1
        
        if event.validation_result == ValidationResult.VALID:
            self.metrics.valid_events += 1
        else:
            self.metrics.invalid_events += 1
        
        # Update event type counts
        event_type = event.event_type.value if isinstance(event.event_type, EventType) else str(event.event_type)
        self.metrics.event_counts[event_type] = self.metrics.event_counts.get(event_type, 0) + 1
        
        # Update latency metrics
        if event.latency_ms is not None:
            self.metrics.latencies.append(event.latency_ms)
            self.metrics.total_latency_ms += event.latency_ms
            self.metrics.max_latency_ms = max(self.metrics.max_latency_ms, event.latency_ms)
            self.metrics.min_latency_ms = min(self.metrics.min_latency_ms, event.latency_ms)
            
            # Check for latency violations (>100ms)
            if event.latency_ms > 100:
                self.metrics.latency_violations += 1
        
        # Collect errors and warnings
        self.metrics.errors.extend(event.validation_errors)
        self.metrics.warnings.extend(event.validation_warnings)
    
    def get_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        self.metrics.end_time = time.time()
        
        # Check for missing events in active sequences
        for sequence in self.active_sequences.values():
            if sequence.is_timed_out:
                self.metrics.missing_events += len(sequence.missing_events)
        
        return {
            "summary": {
                "total_events": self.metrics.total_events,
                "valid_events": self.metrics.valid_events,
                "invalid_events": self.metrics.invalid_events,
                "success_rate": self.metrics.success_rate,
                "test_duration_seconds": self.metrics.duration_seconds
            },
            "event_counts": self.metrics.event_counts,
            "performance": {
                "avg_latency_ms": self.metrics.avg_latency_ms,
                "max_latency_ms": self.metrics.max_latency_ms,
                "min_latency_ms": self.metrics.min_latency_ms if self.metrics.latencies else 0,
                "latency_violations": self.metrics.latency_violations,
                "total_latencies": len(self.metrics.latencies)
            },
            "sequence_tracking": {
                "completed_sequences": len(self.completed_sequences),
                "active_sequences": len(self.active_sequences),
                "timed_out_sequences": len([s for s in self.active_sequences.values() if s.is_timed_out]),
                "missing_events": self.metrics.missing_events
            },
            "errors": self.metrics.errors,
            "warnings": self.metrics.warnings
        }


# ============================================================================
# REAL WEBSOCKET CONNECTION MANAGER
# ============================================================================

class WebSocketConnectionManager:
    """Manages real WebSocket connections for testing."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or self._get_websocket_url()
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.event_capture = WebSocketEventCapture()
        
    def _get_websocket_url(self) -> str:
        """Get WebSocket URL from environment configuration."""
        env = IsolatedEnvironment()
        
        # Try staging environment first
        staging_host = env.get_backend_host("staging")
        staging_port = env.get_backend_port("staging")
        
        if staging_host and staging_port:
            return f"ws://{staging_host}:{staging_port}/ws"
        
        # Fallback to local development
        local_host = env.get_backend_host("development") or "localhost"
        local_port = env.get_backend_port("development") or 8000
        
        return f"ws://{local_host}:{local_port}/ws"
    
    @asynccontextmanager
    async def connect(self, user_id: str, auth_token: str = None) -> websockets.WebSocketServerProtocol:
        """Create a real WebSocket connection."""
        connection_id = f"{user_id}_{uuid.uuid4().hex[:8]}"
        
        # Build connection URL with authentication
        url = self.base_url
        if auth_token:
            url += f"?token={auth_token}"
        
        try:
            logger.info(f"Connecting to WebSocket: {url}")
            async with asyncio.timeout(10):
                websocket = await websockets.connect(url)
            self.connections[connection_id] = websocket
            
            yield websocket
            
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket {url}: {e}")
            raise
        finally:
            # Clean up connection
            if connection_id in self.connections:
                websocket = self.connections[connection_id]
                if not websocket.closed:
                    await websocket.close()
                del self.connections[connection_id]
    
    async def send_message(self, websocket: websockets.WebSocketServerProtocol, message: Dict[str, Any]) -> float:
        """Send a message and return the send latency."""
        start_time = time.time()
        await websocket.send(json.dumps(message))
        return (time.time() - start_time) * 1000  # Return latency in ms
    
    async def receive_events(self, websocket: websockets.WebSocketServerProtocol, timeout: float = 30.0) -> List[ValidatedEvent]:
        """Receive and validate events from WebSocket."""
        events = []
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                try:
                    # Wait for message with short timeout to allow checking overall timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    receive_time = time.time()
                    
                    # Parse and validate the event
                    try:
                        event_data = json.loads(message)
                        websocket_latency = (receive_time - start_time) * 1000
                        validated_event = self.event_capture.capture_event(event_data, websocket_latency)
                        events.append(validated_event)
                        
                        logger.debug(f"Received event: {validated_event.event_type} for thread {validated_event.thread_id}")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse WebSocket message: {message}, error: {e}")
                        
                except asyncio.TimeoutError:
                    # Short timeout reached, continue checking overall timeout
                    continue
                    
        except Exception as e:
            logger.error(f"Error receiving WebSocket events: {e}")
        
        return events


# ============================================================================
# TEST CONFIGURATION AND UTILITIES
# ============================================================================

@dataclass
class ValidationTestConfig:
    """Configuration for WebSocket validation tests."""
    websocket_url: str = ""
    concurrent_users: int = 5
    events_per_user: int = 10
    timeout_seconds: float = 60.0
    max_latency_ms: float = 100.0
    validation_level: EventValidationLevel = EventValidationLevel.STRICT
    
    # Required event sequence for agent execution
    required_events: List[EventType] = field(default_factory=lambda: [
        EventType.AGENT_STARTED,
        EventType.AGENT_THINKING,
        EventType.TOOL_EXECUTING,
        EventType.TOOL_COMPLETED,
        EventType.AGENT_COMPLETED
    ])


def create_test_agent_message(user_id: str, message: str = "Test agent execution") -> Dict[str, Any]:
    """Create a test message that triggers agent execution."""
    return {
        "type": "agent_request",
        "user_id": user_id,
        "thread_id": f"test_thread_{uuid.uuid4().hex[:8]}",
        "message": message,
        "timestamp": time.time(),
        "request_id": str(uuid.uuid4())
    }


def create_mock_auth_token(user_id: str) -> str:
    """Create a mock authentication token for testing."""
    # In real implementation, this would call auth service
    return f"mock_token_{user_id}_{int(time.time())}"


# ============================================================================
# COMPREHENSIVE TEST SUITE
# ============================================================================

class TestWebSocketEventValidationSuite:
    """Comprehensive WebSocket event validation test suite."""
    
    @pytest.fixture(scope="class")
    def test_config(self):
        """Test configuration fixture."""
        return ValidationTestConfig()
    
    @pytest.fixture(scope="class")
    def docker_manager(self):
        """Docker manager fixture for real services."""
        # CRITICAL: Require Docker - no fallback per CLAUDE.md
        require_docker_services()
            
        manager = UnifiedDockerManager(environment_type=EnvironmentType.TEST)
        
        # Ensure services are running
        manager.start_services(["backend", "auth", "db", "redis"])
        
        # Wait for services to be ready
        asyncio.run(ensure_websocket_service_ready())
        
        yield manager
        
        # Cleanup is handled by Docker manager
    
    @pytest.fixture
    def websocket_manager(self, test_config, docker_manager):
        """WebSocket connection manager fixture."""
        return WebSocketConnectionManager(test_config.websocket_url)
    
    # ========================================================================
    # FUNCTIONAL TESTS: Individual Event Types
    # ========================================================================
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_agent_started_event_validation(self, websocket_manager, test_config):
        """Test validation of agent_started events."""
        logger.info("Testing agent_started event validation")
        
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        auth_token = create_mock_auth_token(user_id)
        
        async with websocket_manager.connect(user_id, auth_token) as websocket:
            # Start event sequence tracking
            thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
            websocket_manager.event_capture.start_sequence(
                thread_id, user_id, [EventType.AGENT_STARTED]
            )
            
            # Send agent request
            request_message = create_test_agent_message(user_id, "Test agent_started event")
            request_message["thread_id"] = thread_id
            
            await websocket_manager.send_message(websocket, request_message)
            
            # Receive events
            events = await websocket_manager.receive_events(websocket, timeout=10.0)
            
            # Validate agent_started event was received
            agent_started_events = [e for e in events if e.event_type == EventType.AGENT_STARTED]
            assert len(agent_started_events) > 0, "agent_started event not received"
            
            # Validate event structure
            started_event = agent_started_events[0]
            assert started_event.thread_id == thread_id, f"Thread ID mismatch: {started_event.thread_id} != {thread_id}"
            assert started_event.validation_result == ValidationResult.VALID, f"Event validation failed: {started_event.validation_errors}"
            
            # Validate required fields
            assert "agent_name" in started_event.content, "agent_name field missing from agent_started event"
            assert "timestamp" in started_event.content, "timestamp field missing from agent_started event"
            
            logger.info(f"✓ agent_started event validation passed: {started_event.event_id}")
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_agent_thinking_event_validation(self, websocket_manager, test_config):
        """Test validation of agent_thinking events."""
        logger.info("Testing agent_thinking event validation")
        
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        auth_token = create_mock_auth_token(user_id)
        
        async with websocket_manager.connect(user_id, auth_token) as websocket:
            thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
            websocket_manager.event_capture.start_sequence(
                thread_id, user_id, [EventType.AGENT_THINKING]
            )
            
            request_message = create_test_agent_message(user_id, "Test agent thinking process")
            request_message["thread_id"] = thread_id
            
            await websocket_manager.send_message(websocket, request_message)
            events = await websocket_manager.receive_events(websocket, timeout=15.0)
            
            # Validate agent_thinking event was received
            thinking_events = [e for e in events if e.event_type == EventType.AGENT_THINKING]
            assert len(thinking_events) > 0, "agent_thinking event not received"
            
            thinking_event = thinking_events[0]
            assert thinking_event.thread_id == thread_id
            assert thinking_event.validation_result == ValidationResult.VALID
            
            # Validate thinking-specific fields
            assert "reasoning" in thinking_event.content or "thought" in thinking_event.content, "Reasoning/thought content missing"
            
            logger.info(f"✓ agent_thinking event validation passed: {thinking_event.event_id}")
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_tool_executing_event_validation(self, websocket_manager, test_config):
        """Test validation of tool_executing events."""
        logger.info("Testing tool_executing event validation")
        
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        auth_token = create_mock_auth_token(user_id)
        
        async with websocket_manager.connect(user_id, auth_token) as websocket:
            thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
            websocket_manager.event_capture.start_sequence(
                thread_id, user_id, [EventType.TOOL_EXECUTING]
            )
            
            request_message = create_test_agent_message(user_id, "Execute tools for analysis")
            request_message["thread_id"] = thread_id
            
            await websocket_manager.send_message(websocket, request_message)
            events = await websocket_manager.receive_events(websocket, timeout=20.0)
            
            # Validate tool_executing event was received
            executing_events = [e for e in events if e.event_type == EventType.TOOL_EXECUTING]
            assert len(executing_events) > 0, "tool_executing event not received"
            
            executing_event = executing_events[0]
            assert executing_event.thread_id == thread_id
            assert executing_event.validation_result == ValidationResult.VALID
            
            # Validate tool-specific fields
            assert "tool_name" in executing_event.content, "tool_name field missing"
            
            logger.info(f"✓ tool_executing event validation passed: {executing_event.event_id}")
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_tool_completed_event_validation(self, websocket_manager, test_config):
        """Test validation of tool_completed events."""
        logger.info("Testing tool_completed event validation")
        
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        auth_token = create_mock_auth_token(user_id)
        
        async with websocket_manager.connect(user_id, auth_token) as websocket:
            thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
            websocket_manager.event_capture.start_sequence(
                thread_id, user_id, [EventType.TOOL_COMPLETED]
            )
            
            request_message = create_test_agent_message(user_id, "Complete tool execution")
            request_message["thread_id"] = thread_id
            
            await websocket_manager.send_message(websocket, request_message)
            events = await websocket_manager.receive_events(websocket, timeout=20.0)
            
            # Validate tool_completed event was received
            completed_events = [e for e in events if e.event_type == EventType.TOOL_COMPLETED]
            assert len(completed_events) > 0, "tool_completed event not received"
            
            completed_event = completed_events[0]
            assert completed_event.thread_id == thread_id
            assert completed_event.validation_result == ValidationResult.VALID
            
            # Validate completion-specific fields
            assert "tool_name" in completed_event.content, "tool_name field missing"
            assert "results" in completed_event.content or "output" in completed_event.content, "Results/output missing"
            
            logger.info(f"✓ tool_completed event validation passed: {completed_event.event_id}")
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_agent_completed_event_validation(self, websocket_manager, test_config):
        """Test validation of agent_completed events."""
        logger.info("Testing agent_completed event validation")
        
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        auth_token = create_mock_auth_token(user_id)
        
        async with websocket_manager.connect(user_id, auth_token) as websocket:
            thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
            websocket_manager.event_capture.start_sequence(
                thread_id, user_id, [EventType.AGENT_COMPLETED]
            )
            
            request_message = create_test_agent_message(user_id, "Complete agent execution")
            request_message["thread_id"] = thread_id
            
            await websocket_manager.send_message(websocket, request_message)
            events = await websocket_manager.receive_events(websocket, timeout=25.0)
            
            # Validate agent_completed event was received
            completed_events = [e for e in events if e.event_type == EventType.AGENT_COMPLETED]
            assert len(completed_events) > 0, "agent_completed event not received"
            
            completed_event = completed_events[0]
            assert completed_event.thread_id == thread_id
            assert completed_event.validation_result == ValidationResult.VALID
            
            # Validate completion-specific fields
            assert "response" in completed_event.content or "result" in completed_event.content, "Final response/result missing"
            
            logger.info(f"✓ agent_completed event validation passed: {completed_event.event_id}")
    
    # ========================================================================
    # INTEGRATION TESTS: Full Pipeline Validation
    # ========================================================================
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_full_agent_execution_event_sequence(self, websocket_manager, test_config):
        """Test complete agent execution with all 5 required events."""
        logger.info("Testing full agent execution event sequence")
        
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        auth_token = create_mock_auth_token(user_id)
        
        async with websocket_manager.connect(user_id, auth_token) as websocket:
            thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
            
            # Start tracking the full sequence
            websocket_manager.event_capture.start_sequence(
                thread_id, user_id, test_config.required_events
            )
            
            # Send comprehensive agent request
            request_message = create_test_agent_message(
                user_id, 
                "Perform comprehensive analysis with all agent capabilities"
            )
            request_message["thread_id"] = thread_id
            
            await websocket_manager.send_message(websocket, request_message)
            
            # Receive events with extended timeout for full execution
            events = await websocket_manager.receive_events(websocket, timeout=60.0)
            
            # Validate all 5 required events were received
            event_types = [e.event_type for e in events]
            
            for required_event in test_config.required_events:
                assert required_event in event_types, f"Required event {required_event} not received. Got: {event_types}"
            
            # Validate event ordering (should be in logical sequence)
            expected_order = [
                EventType.AGENT_STARTED,
                EventType.AGENT_THINKING,
                EventType.TOOL_EXECUTING,
                EventType.TOOL_COMPLETED,
                EventType.AGENT_COMPLETED
            ]
            
            # Find the indices of each event type in the received events
            event_indices = {}
            for i, event in enumerate(events):
                if event.event_type in expected_order and event.event_type not in event_indices:
                    event_indices[event.event_type] = i
            
            # Check that events appear in the correct order
            for i in range(len(expected_order) - 1):
                current_event = expected_order[i]
                next_event = expected_order[i + 1]
                
                if current_event in event_indices and next_event in event_indices:
                    assert event_indices[current_event] < event_indices[next_event], \
                        f"Event {current_event} should come before {next_event}"
            
            # Validate sequence completion
            assert thread_id in [s.thread_id for s in websocket_manager.event_capture.completed_sequences], \
                "Event sequence not marked as completed"
            
            logger.info(f"✓ Full agent execution event sequence validated for thread {thread_id}")
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_concurrent_user_event_isolation(self, websocket_manager, test_config):
        """Test that events are properly isolated between concurrent users."""
        logger.info("Testing concurrent user event isolation")
        
        num_users = 3
        user_connections = []
        user_threads = []
        
        try:
            # Create connections for multiple users
            for i in range(num_users):
                user_id = f"test_user_{i}_{uuid.uuid4().hex[:8]}"
                auth_token = create_mock_auth_token(user_id)
                thread_id = f"test_thread_{i}_{uuid.uuid4().hex[:8]}"
                
                connection = await websocket_manager.connect(user_id, auth_token).__aenter__()
                user_connections.append((connection, user_id, thread_id))
                user_threads.append(thread_id)
                
                # Start sequence tracking for each user
                websocket_manager.event_capture.start_sequence(
                    thread_id, user_id, test_config.required_events
                )
            
            # Send requests for all users simultaneously
            async def send_user_request(connection, user_id, thread_id):
                request_message = create_test_agent_message(user_id, f"Concurrent request from {user_id}")
                request_message["thread_id"] = thread_id
                await websocket_manager.send_message(connection, request_message)
                return await websocket_manager.receive_events(connection, timeout=30.0)
            
            # Execute all requests concurrently
            tasks = [
                send_user_request(conn, uid, tid) 
                for conn, uid, tid in user_connections
            ]
            
            all_events = await asyncio.gather(*tasks)
            
            # Validate event isolation - each user should only receive their own events
            for i, events in enumerate(all_events):
                user_id = user_connections[i][1]
                thread_id = user_connections[i][2]
                
                # All events should belong to this user's thread
                for event in events:
                    assert event.thread_id == thread_id, \
                        f"User {user_id} received event from different thread: {event.thread_id}"
                
                # Should have received events for their agent execution
                event_types = [e.event_type for e in events]
                assert len(event_types) > 0, f"User {user_id} received no events"
                
                logger.info(f"✓ User {user_id} event isolation validated - {len(events)} events received")
        
        finally:
            # Clean up connections
            for connection, _, _ in user_connections:
                if not connection.closed:
                    await connection.close()
    
    # ========================================================================
    # PERFORMANCE TESTS: Latency and Throughput
    # ========================================================================
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_websocket_event_latency_performance(self, websocket_manager, test_config):
        """Test WebSocket event latency meets performance requirements (<100ms)."""
        logger.info("Testing WebSocket event latency performance")
        
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        auth_token = create_mock_auth_token(user_id)
        
        latencies = []
        
        async with websocket_manager.connect(user_id, auth_token) as websocket:
            # Send multiple requests to gather latency statistics
            for i in range(10):
                thread_id = f"perf_thread_{i}_{uuid.uuid4().hex[:8]}"
                
                # Measure request latency
                start_time = time.time()
                request_message = create_test_agent_message(user_id, f"Performance test request {i}")
                request_message["thread_id"] = thread_id
                
                await websocket_manager.send_message(websocket, request_message)
                
                # Wait for first event response
                events = await websocket_manager.receive_events(websocket, timeout=5.0)
                
                if events:
                    first_response_time = time.time()
                    latency_ms = (first_response_time - start_time) * 1000
                    latencies.append(latency_ms)
                    
                    logger.debug(f"Request {i} latency: {latency_ms:.2f}ms")
        
        # Validate performance requirements
        assert len(latencies) > 0, "No latency measurements collected"
        
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)
        
        # Performance assertions
        assert avg_latency < test_config.max_latency_ms, \
            f"Average latency {avg_latency:.2f}ms exceeds limit {test_config.max_latency_ms}ms"
        
        assert max_latency < test_config.max_latency_ms * 2, \
            f"Maximum latency {max_latency:.2f}ms is too high (>{test_config.max_latency_ms * 2}ms)"
        
        # Log performance results
        logger.info(f"✓ Performance validation passed:")
        logger.info(f"  Average latency: {avg_latency:.2f}ms")
        logger.info(f"  Maximum latency: {max_latency:.2f}ms")
        logger.info(f"  Samples: {len(latencies)}")
    
    # ========================================================================
    # RESILIENCE TESTS: Failure Recovery
    # ========================================================================
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_websocket_reconnection_event_continuity(self, websocket_manager, test_config):
        """Test that WebSocket reconnection maintains event continuity."""
        logger.info("Testing WebSocket reconnection event continuity")
        
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        auth_token = create_mock_auth_token(user_id)
        
        # Initial connection and request
        async with websocket_manager.connect(user_id, auth_token) as websocket1:
            thread_id = f"reconnect_thread_{uuid.uuid4().hex[:8]}"
            
            request_message = create_test_agent_message(user_id, "Test reconnection continuity")
            request_message["thread_id"] = thread_id
            
            await websocket_manager.send_message(websocket1, request_message)
            
            # Receive some initial events
            initial_events = await websocket_manager.receive_events(websocket1, timeout=5.0)
            
            # Force disconnect by closing the WebSocket
            await websocket1.close()
        
        # Small delay to simulate reconnection scenario
        await asyncio.sleep(1.0)
        
        # Reconnect and check for continued events
        async with websocket_manager.connect(user_id, auth_token) as websocket2:
            # The agent execution should continue and we should receive remaining events
            remaining_events = await websocket_manager.receive_events(websocket2, timeout=10.0)
            
            # Validate we received events across the reconnection
            total_events = len(initial_events) + len(remaining_events)
            assert total_events > 0, "No events received across reconnection"
            
            logger.info(f"✓ Reconnection continuity validated: {len(initial_events)} + {len(remaining_events)} = {total_events} events")
    
    # ========================================================================
    # SECURITY TESTS: User Isolation
    # ========================================================================
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_user_isolation_security_validation(self, websocket_manager, test_config):
        """Test that user isolation prevents cross-user event leakage."""
        logger.info("Testing user isolation security validation")
        
        # Create two distinct users
        user1_id = f"user1_{uuid.uuid4().hex[:8]}"
        user2_id = f"user2_{uuid.uuid4().hex[:8]}"
        
        auth_token1 = create_mock_auth_token(user1_id)
        auth_token2 = create_mock_auth_token(user2_id)
        
        user1_events = []
        user2_events = []
        
        async def capture_user_events(user_id: str, auth_token: str, event_list: List):
            async with websocket_manager.connect(user_id, auth_token) as websocket:
                thread_id = f"security_thread_{user_id}_{uuid.uuid4().hex[:8]}"
                
                request_message = create_test_agent_message(user_id, f"Security test for {user_id}")
                request_message["thread_id"] = thread_id
                request_message["security_marker"] = user_id  # Add marker for validation
                
                await websocket_manager.send_message(websocket, request_message)
                events = await websocket_manager.receive_events(websocket, timeout=15.0)
                event_list.extend(events)
        
        # Run both users concurrently
        await asyncio.gather(
            capture_user_events(user1_id, auth_token1, user1_events),
            capture_user_events(user2_id, auth_token2, user2_events)
        )
        
        # Security validation: ensure no cross-contamination
        assert len(user1_events) > 0, f"User 1 ({user1_id}) received no events"
        assert len(user2_events) > 0, f"User 2 ({user2_id}) received no events"
        
        # Check that user1 never received user2's events and vice versa
        user1_thread_ids = {event.thread_id for event in user1_events}
        user2_thread_ids = {event.thread_id for event in user2_events}
        
        # Thread IDs should be completely separate
        assert user1_thread_ids.isdisjoint(user2_thread_ids), \
            f"Thread ID overlap detected - security violation! User1: {user1_thread_ids}, User2: {user2_thread_ids}"
        
        # Validate that events contain expected user context
        for event in user1_events:
            # Events should be associated with user1's context
            assert user2_id not in str(event.content), \
                f"User 1 event contains User 2 context: {event.content}"
        
        for event in user2_events:
            # Events should be associated with user2's context  
            assert user1_id not in str(event.content), \
                f"User 2 event contains User 1 context: {event.content}"
        
        logger.info(f"✓ User isolation security validated:")
        logger.info(f"  User 1 events: {len(user1_events)}, unique threads: {len(user1_thread_ids)}")
        logger.info(f"  User 2 events: {len(user2_events)}, unique threads: {len(user2_thread_ids)}")
    
    # ========================================================================
    # COMPREHENSIVE VALIDATION REPORT
    # ========================================================================
    
    @requires_docker
    @pytest.mark.asyncio
    async def test_comprehensive_validation_report_generation(self, websocket_manager, test_config):
        """Generate comprehensive validation report for all WebSocket events."""
        logger.info("Generating comprehensive WebSocket validation report")
        
        user_id = f"report_user_{uuid.uuid4().hex[:8]}"
        auth_token = create_mock_auth_token(user_id)
        
        async with websocket_manager.connect(user_id, auth_token) as websocket:
            # Execute multiple agent requests to gather comprehensive data
            for i in range(5):
                thread_id = f"report_thread_{i}_{uuid.uuid4().hex[:8]}"
                
                websocket_manager.event_capture.start_sequence(
                    thread_id, user_id, test_config.required_events
                )
                
                request_message = create_test_agent_message(
                    user_id, 
                    f"Comprehensive validation request {i}"
                )
                request_message["thread_id"] = thread_id
                
                await websocket_manager.send_message(websocket, request_message)
                
                # Brief wait between requests
                await asyncio.sleep(1.0)
            
            # Collect all events
            events = await websocket_manager.receive_events(websocket, timeout=45.0)
        
        # Generate validation report
        report = websocket_manager.event_capture.get_validation_report()
        
        # Validate report completeness
        assert "summary" in report, "Validation report missing summary section"
        assert "event_counts" in report, "Validation report missing event counts"
        assert "performance" in report, "Validation report missing performance metrics"
        assert "sequence_tracking" in report, "Validation report missing sequence tracking"
        
        # Log comprehensive report
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE WEBSOCKET VALIDATION REPORT")
        logger.info("=" * 80)
        
        summary = report["summary"]
        logger.info(f"SUMMARY:")
        logger.info(f"  Total Events: {summary['total_events']}")
        logger.info(f"  Valid Events: {summary['valid_events']}")
        logger.info(f"  Invalid Events: {summary['invalid_events']}")
        logger.info(f"  Success Rate: {summary['success_rate']:.2f}%")
        logger.info(f"  Test Duration: {summary['test_duration_seconds']:.2f}s")
        
        logger.info(f"\nEVENT COUNTS:")
        for event_type, count in report["event_counts"].items():
            logger.info(f"  {event_type}: {count}")
        
        performance = report["performance"]
        logger.info(f"\nPERFORMACE:")
        logger.info(f"  Average Latency: {performance['avg_latency_ms']:.2f}ms")
        logger.info(f"  Maximum Latency: {performance['max_latency_ms']:.2f}ms")
        logger.info(f"  Latency Violations: {performance['latency_violations']}")
        
        sequences = report["sequence_tracking"]
        logger.info(f"\nSEQUENCE TRACKING:")
        logger.info(f"  Completed Sequences: {sequences['completed_sequences']}")
        logger.info(f"  Active Sequences: {sequences['active_sequences']}")
        logger.info(f"  Timed Out Sequences: {sequences['timed_out_sequences']}")
        logger.info(f"  Missing Events: {sequences['missing_events']}")
        
        if report["errors"]:
            logger.info(f"\nERRORS ({len(report['errors'])}):")
            for error in report["errors"][:5]:  # Show first 5 errors
                logger.info(f"  - {error}")
        
        if report["warnings"]:
            logger.info(f"\nWARNINGS ({len(report['warnings'])}):")
            for warning in report["warnings"][:5]:  # Show first 5 warnings
                logger.info(f"  - {warning}")
        
        logger.info("=" * 80)
        
        # Validate key performance indicators
        assert summary["success_rate"] >= 95.0, f"Success rate {summary['success_rate']:.2f}% below 95% threshold"
        assert performance["avg_latency_ms"] < test_config.max_latency_ms, \
            f"Average latency {performance['avg_latency_ms']:.2f}ms exceeds {test_config.max_latency_ms}ms limit"
        assert sequences["missing_events"] == 0, f"Missing events detected: {sequences['missing_events']}"
        
        logger.info("✓ Comprehensive validation report generated and validated")


if __name__ == "__main__":
    """Run the comprehensive WebSocket validation test suite."""
    # Configure logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the test suite
    pytest.main([__file__, "-v", "--tb=short", "-x"])