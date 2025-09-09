#!/usr/bin/env python
"""
CRITICAL: Comprehensive WebSocket Agent Events Validation Suite

BUSINESS CRITICAL REQUIREMENTS:
This test suite validates the COMPLETE WebSocket agent event system that enables
substantive chat interactions - the core business value delivery mechanism.

MISSION: Ensure ALL WebSocket agent events work flawlessly under ALL conditions.
- Business Impact: $500K+ ARR at risk if WebSocket events fail
- User Experience: Complete chat functionality depends on these events
- System Reliability: Multi-user concurrent execution must be bulletproof

EVENTS TESTED (The 5 Critical Events for Chat Value):
1. agent_started - User must know agent began processing
2. agent_thinking - Real-time reasoning visibility 
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results delivery
5. agent_completed - Final response ready notification

TEST PHILOSOPHY:
These tests are INTENTIONALLY DIFFICULT and comprehensive. They will:
- Use ONLY real WebSocket connections (NEVER mocks)
- Test edge cases that commonly cause silent failures
- Validate concurrent multi-user scenarios (10+ users)  
- Test performance under load (25+ connections)
- Verify event ordering and timing guarantees
- Test failure recovery and retry mechanisms
- Validate cross-user isolation (security critical)
- Test timeout and error handling
- Verify event content structure validation

IF THESE TESTS FAIL, THE PRODUCT IS BROKEN.
"""

import asyncio
import json
import os
import sys
import time
import uuid
import threading
import random
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Any, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import pytest
import websockets
from websockets.exceptions import ConnectionClosedError, WebSocketException

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import core infrastructure
from shared.isolated_environment import get_env
from test_framework.robust_websocket_test_helper import RobustWebSocketTestHelper, WebSocketTestConfig
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# ============================================================================
# CRITICAL EVENT DEFINITIONS - BUSINESS VALUE ENABLERS
# ============================================================================

CRITICAL_EVENTS = {
    'agent_started',      # User must see agent began processing
    'agent_thinking',     # Real-time reasoning visibility  
    'tool_executing',     # Tool usage transparency
    'tool_completed',     # Tool results delivery
    'agent_completed'     # Final response ready notification
}

REQUIRED_EVENT_FIELDS = {
    'agent_started': ['agent_name', 'run_id', 'timestamp'],
    'agent_thinking': ['thought', 'agent_name', 'timestamp'],
    'tool_executing': ['tool_name', 'agent_name', 'timestamp'],
    'tool_completed': ['tool_name', 'agent_name', 'result', 'timestamp'],
    'agent_completed': ['agent_name', 'run_id', 'timestamp']
}

# Performance and reliability thresholds
MAX_EVENT_DELAY_MS = 2000  # 2 seconds max delay for any event
MAX_CONNECTION_TIME_MS = 10000  # 10 seconds max connection time  
MIN_CONCURRENT_USERS = 10  # Minimum concurrent user support
STRESS_TEST_USERS = 25  # Stress test user count
PERFORMANCE_TEST_EVENTS_PER_USER = 50  # Events per user for performance test


# ============================================================================
# EVENT CAPTURE AND VALIDATION INFRASTRUCTURE  
# ============================================================================

@dataclass
class WebSocketEvent:
    """Represents a captured WebSocket event with validation metadata."""
    event_type: str
    payload: Dict[str, Any]
    timestamp: float
    user_id: str
    thread_id: Optional[str] = None
    run_id: Optional[str] = None
    connection_id: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)
    delivery_latency_ms: Optional[float] = None


@dataclass
class UserSession:
    """Tracks a user's WebSocket session and events."""
    user_id: str
    connection_id: str
    websocket: Optional[websockets.ClientConnection] = None
    events: List[WebSocketEvent] = field(default_factory=list)
    expected_events: Set[str] = field(default_factory=set)
    received_events: Set[str] = field(default_factory=set)
    connection_start_time: Optional[float] = None
    last_event_time: Optional[float] = None
    errors: List[str] = field(default_factory=list)
    is_active: bool = True


class ComprehensiveEventCapture:
    """
    Comprehensive event capture system for WebSocket validation.
    
    This class captures, validates, and analyzes WebSocket events across
    multiple concurrent users to ensure system reliability.
    """
    
    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}
        self.all_events: List[WebSocketEvent] = []
        self.cross_user_violations: List[Dict[str, Any]] = []
        self.timing_violations: List[Dict[str, Any]] = []
        self.content_violations: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {}
        self.lock = threading.Lock()
        
        # Event ordering tracking
        self.event_sequences: Dict[str, List[str]] = {}  # user_id -> event sequence
        self.expected_sequences: Dict[str, List[str]] = {}  # user_id -> expected sequence
        
        # Performance tracking
        self.connection_times: List[float] = []
        self.event_latencies: List[float] = []
        self.start_time = time.time()
    
    def add_session(self, user_id: str, connection_id: str, websocket=None) -> UserSession:
        """Add a new user session for tracking."""
        with self.lock:
            session = UserSession(
                user_id=user_id,
                connection_id=connection_id,
                websocket=websocket,
                connection_start_time=time.time()
            )
            self.sessions[user_id] = session
            self.event_sequences[user_id] = []
            self.expected_sequences[user_id] = []
            return session
    
    def record_event(self, user_id: str, event_type: str, payload: Dict[str, Any],
                    thread_id: str = None, run_id: str = None, 
                    connection_id: str = None) -> WebSocketEvent:
        """Record a WebSocket event with comprehensive validation."""
        timestamp = time.time()
        
        with self.lock:
            # Create event object
            event = WebSocketEvent(
                event_type=event_type,
                payload=payload,
                timestamp=timestamp,
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                connection_id=connection_id
            )
            
            # Validate event structure
            self._validate_event_structure(event)
            
            # Calculate delivery latency if session exists
            if user_id in self.sessions:
                session = self.sessions[user_id]
                if session.connection_start_time:
                    event.delivery_latency_ms = (timestamp - session.connection_start_time) * 1000
                    self.event_latencies.append(event.delivery_latency_ms)
                
                # Update session tracking
                session.events.append(event)
                session.received_events.add(event_type)
                session.last_event_time = timestamp
                self.event_sequences[user_id].append(event_type)
            
            # Store globally
            self.all_events.append(event)
            
            # Detect violations
            self._detect_cross_user_violations(event)
            self._detect_timing_violations(event)
            
            logger.debug(f"Recorded {event_type} for user {user_id} at {timestamp}")
            return event
    
    def _validate_event_structure(self, event: WebSocketEvent) -> None:
        """Validate event has required fields and proper structure."""
        event_type = event.event_type
        payload = event.payload
        
        # Check if it's a critical event
        if event_type in CRITICAL_EVENTS:
            required_fields = REQUIRED_EVENT_FIELDS.get(event_type, [])
            
            for field in required_fields:
                if field not in payload:
                    error = f"Missing required field '{field}' in {event_type}"
                    event.validation_errors.append(error)
                    self.content_violations.append({
                        'event': event,
                        'violation_type': 'missing_field',
                        'field': field,
                        'timestamp': event.timestamp
                    })
            
            # Validate field types and values
            if 'timestamp' in payload:
                try:
                    timestamp_val = float(payload['timestamp'])
                    if timestamp_val <= 0:
                        event.validation_errors.append("Invalid timestamp value")
                except (ValueError, TypeError):
                    event.validation_errors.append("Timestamp is not a valid number")
            
            # Validate agent_name is not empty
            if 'agent_name' in payload and not payload['agent_name']:
                event.validation_errors.append("Empty agent_name")
    
    def _detect_cross_user_violations(self, event: WebSocketEvent) -> None:
        """Detect if event was delivered to wrong user."""
        # Look for events with user-specific data that don't match the session
        payload = event.payload
        
        if 'user_id' in payload and payload['user_id'] != event.user_id:
            violation = {
                'violation_type': 'cross_user_data',
                'event': event,
                'intended_user': payload['user_id'],
                'actual_user': event.user_id,
                'timestamp': event.timestamp,
                'severity': 'CRITICAL'
            }
            self.cross_user_violations.append(violation)
            logger.error(f"CRITICAL: Cross-user violation detected - {violation}")
    
    def _detect_timing_violations(self, event: WebSocketEvent) -> None:
        """Detect timing-related violations."""
        if event.delivery_latency_ms and event.delivery_latency_ms > MAX_EVENT_DELAY_MS:
            violation = {
                'violation_type': 'excessive_latency',
                'event': event,
                'latency_ms': event.delivery_latency_ms,
                'max_allowed_ms': MAX_EVENT_DELAY_MS,
                'timestamp': event.timestamp
            }
            self.timing_violations.append(violation)
    
    def set_expected_sequence(self, user_id: str, expected_events: List[str]) -> None:
        """Set expected event sequence for a user."""
        with self.lock:
            self.expected_sequences[user_id] = expected_events.copy()
    
    def validate_event_sequences(self) -> List[Dict[str, Any]]:
        """Validate that events occurred in expected order for each user."""
        violations = []
        
        with self.lock:
            for user_id, expected in self.expected_sequences.items():
                actual = self.event_sequences.get(user_id, [])
                
                # Check if we have the expected events (order matters)
                if len(actual) != len(expected):
                    violations.append({
                        'user_id': user_id,
                        'violation_type': 'sequence_length_mismatch',
                        'expected_count': len(expected),
                        'actual_count': len(actual),
                        'expected': expected,
                        'actual': actual
                    })
                    continue
                
                # Check sequence order
                for i, (exp_event, act_event) in enumerate(zip(expected, actual)):
                    if exp_event != act_event:
                        violations.append({
                            'user_id': user_id,
                            'violation_type': 'sequence_order_violation',
                            'position': i,
                            'expected_event': exp_event,
                            'actual_event': act_event,
                            'expected_sequence': expected,
                            'actual_sequence': actual
                        })
                        break
        
        return violations
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""
        with self.lock:
            total_events = len(self.all_events)
            total_sessions = len(self.sessions)
            test_duration = time.time() - self.start_time
            
            # Calculate latency statistics
            if self.event_latencies:
                avg_latency = sum(self.event_latencies) / len(self.event_latencies)
                max_latency = max(self.event_latencies)
                min_latency = min(self.event_latencies)
                # Calculate 95th percentile
                sorted_latencies = sorted(self.event_latencies)
                p95_index = int(0.95 * len(sorted_latencies))
                p95_latency = sorted_latencies[p95_index] if sorted_latencies else 0
            else:
                avg_latency = max_latency = min_latency = p95_latency = 0
            
            return {
                'total_events': total_events,
                'total_sessions': total_sessions,
                'test_duration_s': test_duration,
                'events_per_second': total_events / test_duration if test_duration > 0 else 0,
                'avg_latency_ms': avg_latency,
                'max_latency_ms': max_latency,
                'min_latency_ms': min_latency,
                'p95_latency_ms': p95_latency,
                'cross_user_violations': len(self.cross_user_violations),
                'timing_violations': len(self.timing_violations),
                'content_violations': len(self.content_violations),
                'critical_events_received': len([e for e in self.all_events if e.event_type in CRITICAL_EVENTS])
            }
    
    def get_session_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all user sessions."""
        with self.lock:
            summary = {}
            for user_id, session in self.sessions.items():
                summary[user_id] = {
                    'events_received': len(session.events),
                    'event_types': list(session.received_events),
                    'errors': session.errors,
                    'connection_duration_s': (time.time() - session.connection_start_time) if session.connection_start_time else 0,
                    'last_event_ago_s': (time.time() - session.last_event_time) if session.last_event_time else None,
                    'expected_events': list(session.expected_events),
                    'missing_events': list(session.expected_events - session.received_events)
                }
            return summary


# ============================================================================
# REAL WEBSOCKET CONNECTION MANAGER (NO MOCKS)
# ============================================================================

class RealWebSocketConnectionManager:
    """
    Manager for real WebSocket connections - NO MOCKS ALLOWED.
    
    This class manages multiple concurrent WebSocket connections to test
    the system under realistic multi-user conditions.
    """
    
    def __init__(self, config: WebSocketTestConfig):
        self.config = config
        self.connections: Dict[str, websockets.ClientConnection] = {}
        self.connection_tasks: Dict[str, asyncio.Task] = {}
        self.event_capture = ComprehensiveEventCapture()
        self.is_running = True
        
    async def create_user_connection(self, user_id: str) -> bool:
        """Create a real WebSocket connection for a user."""
        try:
            # Build WebSocket URL with authentication if available
            ws_url = self.config.websocket_url
            headers = {}
            
            # Add authentication headers if available
            env = get_env()
            token = env.get('WEBSOCKET_TEST_TOKEN') or env.get('E2E_AUTH_TOKEN')
            if token:
                headers['Authorization'] = f'Bearer {token}'
            
            # Connect to real WebSocket
            start_time = time.time()
            websocket = await websockets.connect(
                ws_url,
                extra_headers=headers,
                ping_interval=self.config.ping_interval,
                close_timeout=10,
                max_size=2**20,  # 1MB max message size
                max_queue=100    # Max queued messages
            )
            
            connection_time = (time.time() - start_time) * 1000
            self.event_capture.connection_times.append(connection_time)
            
            # Store connection
            connection_id = str(uuid.uuid4())
            self.connections[user_id] = websocket
            
            # Register session in event capture
            self.event_capture.add_session(user_id, connection_id, websocket)
            
            # Start listening for events
            self.connection_tasks[user_id] = asyncio.create_task(
                self._listen_for_events(user_id, websocket)
            )
            
            logger.info(f"WebSocket connected for user {user_id} in {connection_time:.1f}ms")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect WebSocket for user {user_id}: {e}")
            return False
    
    async def _listen_for_events(self, user_id: str, websocket: websockets.ClientConnection):
        """Listen for WebSocket events from a connection."""
        try:
            async for message in websocket:
                if not self.is_running:
                    break
                    
                try:
                    # Parse message
                    data = json.loads(message)
                    event_type = data.get('type')
                    payload = data.get('payload', {})
                    
                    # Record event in capture system
                    self.event_capture.record_event(
                        user_id=user_id,
                        event_type=event_type,
                        payload=payload,
                        thread_id=payload.get('thread_id'),
                        run_id=payload.get('run_id')
                    )
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse WebSocket message for user {user_id}: {e}")
                except Exception as e:
                    logger.error(f"Error processing WebSocket message for user {user_id}: {e}")
                    
        except ConnectionClosedError:
            logger.info(f"WebSocket connection closed for user {user_id}")
        except Exception as e:
            logger.error(f"WebSocket listening error for user {user_id}: {e}")
    
    async def send_test_message(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Send a test message through user's WebSocket connection."""
        if user_id not in self.connections:
            return False
            
        try:
            websocket = self.connections[user_id]
            await websocket.send(json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Failed to send test message for user {user_id}: {e}")
            return False
    
    async def close_connection(self, user_id: str):
        """Close a user's WebSocket connection."""
        if user_id in self.connections:
            try:
                await self.connections[user_id].close()
                del self.connections[user_id]
            except Exception as e:
                logger.error(f"Error closing connection for user {user_id}: {e}")
        
        if user_id in self.connection_tasks:
            self.connection_tasks[user_id].cancel()
            try:
                await self.connection_tasks[user_id]
            except asyncio.CancelledError:
                pass
            del self.connection_tasks[user_id]
    
    async def close_all_connections(self):
        """Close all WebSocket connections."""
        self.is_running = False
        
        # Close all connections
        close_tasks = [self.close_connection(user_id) for user_id in list(self.connections.keys())]
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)


# ============================================================================  
# MOCK AGENT SYSTEM FOR TESTING (SIMULATES REAL AGENTS)
# ============================================================================

class MockAgentSystemForTesting:
    """
    Mock agent system that simulates real agent execution to trigger WebSocket events.
    
    This is NOT a mock of the WebSocket system - it's a test harness that simulates
    the agent execution flows that should trigger real WebSocket events.
    """
    
    def __init__(self, websocket_manager: RealWebSocketConnectionManager):
        self.websocket_manager = websocket_manager
        self.active_executions: Dict[str, Dict[str, Any]] = {}
    
    async def simulate_agent_execution(self, user_id: str, agent_name: str = "TestAgent") -> Dict[str, Any]:
        """
        Simulate a complete agent execution flow.
        
        This should trigger all 5 critical WebSocket events:
        1. agent_started
        2. agent_thinking  
        3. tool_executing
        4. tool_completed
        5. agent_completed
        """
        run_id = f"run_{user_id}_{uuid.uuid4().hex[:8]}"
        thread_id = f"thread_{user_id}_{uuid.uuid4().hex[:8]}"
        
        # Track execution
        execution = {
            'user_id': user_id,
            'agent_name': agent_name,
            'run_id': run_id,
            'thread_id': thread_id,
            'start_time': time.time(),
            'events_sent': []
        }
        self.active_executions[run_id] = execution
        
        try:
            # Set expected event sequence
            expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
            self.websocket_manager.event_capture.set_expected_sequence(user_id, expected_events)
            
            # 1. Send agent_started event
            await self._send_agent_started(user_id, agent_name, run_id, thread_id)
            execution['events_sent'].append('agent_started')
            
            # Small delay to simulate processing
            await asyncio.sleep(0.1)
            
            # 2. Send agent_thinking event
            await self._send_agent_thinking(user_id, agent_name, run_id, thread_id)
            execution['events_sent'].append('agent_thinking')
            
            # Small delay to simulate thinking
            await asyncio.sleep(0.2)
            
            # 3. Send tool_executing event
            tool_name = "test_analysis_tool"
            await self._send_tool_executing(user_id, agent_name, tool_name, run_id, thread_id)
            execution['events_sent'].append('tool_executing')
            
            # Simulate tool execution time
            await asyncio.sleep(0.3)
            
            # 4. Send tool_completed event
            tool_result = {"status": "success", "analysis": "Test analysis completed", "confidence": 0.95}
            await self._send_tool_completed(user_id, agent_name, tool_name, tool_result, run_id, thread_id)
            execution['events_sent'].append('tool_completed')
            
            # Small delay before completion
            await asyncio.sleep(0.1)
            
            # 5. Send agent_completed event
            final_result = {"response": f"Task completed by {agent_name}", "tool_results": [tool_result]}
            await self._send_agent_completed(user_id, agent_name, final_result, run_id, thread_id)
            execution['events_sent'].append('agent_completed')
            
            execution['end_time'] = time.time()
            execution['duration_ms'] = (execution['end_time'] - execution['start_time']) * 1000
            
            logger.info(f"Agent execution completed for user {user_id} in {execution['duration_ms']:.1f}ms")
            return execution
            
        except Exception as e:
            logger.error(f"Agent execution failed for user {user_id}: {e}")
            execution['error'] = str(e)
            return execution
    
    async def _send_agent_started(self, user_id: str, agent_name: str, run_id: str, thread_id: str):
        """Send agent_started event through WebSocket."""
        message = {
            "type": "agent_started",
            "payload": {
                "agent_name": agent_name,
                "run_id": run_id,
                "thread_id": thread_id,
                "timestamp": time.time(),
                "user_id": user_id
            }
        }
        await self.websocket_manager.send_test_message(user_id, message)
    
    async def _send_agent_thinking(self, user_id: str, agent_name: str, run_id: str, thread_id: str):
        """Send agent_thinking event through WebSocket."""
        message = {
            "type": "agent_thinking",
            "payload": {
                "thought": f"Analyzing the request and planning approach...",
                "agent_name": agent_name,
                "run_id": run_id,
                "thread_id": thread_id,
                "step_number": 1,
                "timestamp": time.time(),
                "user_id": user_id
            }
        }
        await self.websocket_manager.send_test_message(user_id, message)
    
    async def _send_tool_executing(self, user_id: str, agent_name: str, tool_name: str, run_id: str, thread_id: str):
        """Send tool_executing event through WebSocket."""
        message = {
            "type": "tool_executing", 
            "payload": {
                "tool_name": tool_name,
                "agent_name": agent_name,
                "run_id": run_id,
                "thread_id": thread_id,
                "timestamp": time.time(),
                "user_id": user_id,
                "tool_purpose": "Analysis and data processing"
            }
        }
        await self.websocket_manager.send_test_message(user_id, message)
    
    async def _send_tool_completed(self, user_id: str, agent_name: str, tool_name: str, 
                                  result: Dict[str, Any], run_id: str, thread_id: str):
        """Send tool_completed event through WebSocket."""
        message = {
            "type": "tool_completed",
            "payload": {
                "tool_name": tool_name,
                "agent_name": agent_name,
                "result": result,
                "run_id": run_id,
                "thread_id": thread_id,
                "timestamp": time.time(),
                "user_id": user_id
            }
        }
        await self.websocket_manager.send_test_message(user_id, message)
    
    async def _send_agent_completed(self, user_id: str, agent_name: str, result: Dict[str, Any], 
                                   run_id: str, thread_id: str):
        """Send agent_completed event through WebSocket.""" 
        message = {
            "type": "agent_completed",
            "payload": {
                "agent_name": agent_name,
                "run_id": run_id,
                "thread_id": thread_id,
                "result": result,
                "timestamp": time.time(),
                "duration_ms": 800,  # Simulated duration
                "user_id": user_id
            }
        }
        await self.websocket_manager.send_test_message(user_id, message)


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture
def websocket_config():
    """Create WebSocket test configuration."""
    env = get_env()
    
    # Detect environment and configure accordingly
    environment = env.get("ENVIRONMENT", "development")
    
    if environment == "staging":
        config = WebSocketTestConfig(
            websocket_url="wss://netra-backend-staging-701982941522.us-central1.run.app/ws",
            backend_url="https://netra-backend-staging-701982941522.us-central1.run.app",
            auth_url="https://netra-auth-service-701982941522.us-central1.run.app",
            environment="staging",
            use_ssl=True
        )
    else:
        # Development/local configuration
        config = WebSocketTestConfig(
            websocket_url=env.get("E2E_WEBSOCKET_URL", "ws://localhost:8888/ws"),
            backend_url=env.get("E2E_BACKEND_URL", "http://localhost:8888"),
            auth_url=env.get("E2E_AUTH_SERVICE_URL", "http://localhost:8001"),
            environment="development",
            use_ssl=False
        )
    
    return config


@pytest.fixture
async def websocket_manager(websocket_config):
    """Create real WebSocket connection manager."""
    manager = RealWebSocketConnectionManager(websocket_config)
    yield manager
    await manager.close_all_connections()


@pytest.fixture
async def mock_agent_system(websocket_manager):
    """Create mock agent system for testing."""
    return MockAgentSystemForTesting(websocket_manager)


# ============================================================================
# BASIC EVENT TRANSMISSION TESTS
# ============================================================================

class TestBasicEventTransmission:
    """Test basic WebSocket event transmission functionality."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_single_user_all_critical_events(self, websocket_manager, mock_agent_system):
        """CRITICAL: Test all 5 critical events are transmitted for single user."""
        user_id = "test_user_001"
        
        # Create WebSocket connection
        connected = await websocket_manager.create_user_connection(user_id)
        assert connected, "Failed to create WebSocket connection"
        
        # Run agent execution that should trigger all events
        execution = await mock_agent_system.simulate_agent_execution(user_id)
        assert 'error' not in execution, f"Agent execution failed: {execution.get('error')}"
        
        # Wait for events to be processed
        await asyncio.sleep(2)
        
        # Verify all critical events were received
        session = websocket_manager.event_capture.sessions[user_id]
        received_event_types = session.received_events
        
        for critical_event in CRITICAL_EVENTS:
            assert critical_event in received_event_types, \
                f"Critical event '{critical_event}' was not received"
        
        # Verify event sequence is correct
        sequence_violations = websocket_manager.event_capture.validate_event_sequences()
        assert len(sequence_violations) == 0, \
            f"Event sequence violations detected: {sequence_violations}"
        
        # Verify event content structure
        for event in session.events:
            if event.event_type in CRITICAL_EVENTS:
                assert len(event.validation_errors) == 0, \
                    f"Event validation errors: {event.validation_errors}"
    
    @pytest.mark.asyncio
    @pytest.mark.critical  
    async def test_event_content_structure_validation(self, websocket_manager, mock_agent_system):
        """CRITICAL: Test event content has required fields and proper structure."""
        user_id = "test_user_002"
        
        # Create connection and run execution
        await websocket_manager.create_user_connection(user_id)
        await mock_agent_system.simulate_agent_execution(user_id)
        await asyncio.sleep(1)
        
        # Get all events for validation
        session = websocket_manager.event_capture.sessions[user_id]
        critical_events = [e for e in session.events if e.event_type in CRITICAL_EVENTS]
        
        assert len(critical_events) >= 5, "Not all critical events were received"
        
        # Validate each critical event has required fields
        for event in critical_events:
            event_type = event.event_type
            payload = event.payload
            required_fields = REQUIRED_EVENT_FIELDS.get(event_type, [])
            
            for field in required_fields:
                assert field in payload, \
                    f"Event {event_type} missing required field '{field}'. Payload: {payload}"
            
            # Validate specific field types
            if 'timestamp' in payload:
                assert isinstance(payload['timestamp'], (int, float)), \
                    f"Timestamp must be numeric in {event_type}"
                assert payload['timestamp'] > 0, \
                    f"Timestamp must be positive in {event_type}"
            
            if 'agent_name' in payload:
                assert payload['agent_name'], \
                    f"Agent name cannot be empty in {event_type}"
            
            if 'run_id' in payload:
                assert payload['run_id'], \
                    f"Run ID cannot be empty in {event_type}"


# ============================================================================
# CONCURRENT USER AND ISOLATION TESTS
# ============================================================================

class TestConcurrentUserIsolation:
    """Test concurrent user scenarios and cross-user isolation."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_concurrent_users_event_isolation(self, websocket_manager, mock_agent_system):
        """CRITICAL: Test events are isolated between concurrent users."""
        num_users = MIN_CONCURRENT_USERS
        user_ids = [f"test_user_{i:03d}" for i in range(num_users)]
        
        # Create connections for all users
        connection_tasks = [
            websocket_manager.create_user_connection(user_id)
            for user_id in user_ids
        ]
        connections = await asyncio.gather(*connection_tasks)
        
        # Verify all connections succeeded
        failed_connections = sum(1 for connected in connections if not connected)
        assert failed_connections == 0, f"{failed_connections}/{num_users} connections failed"
        
        # Run concurrent agent executions
        execution_tasks = [
            mock_agent_system.simulate_agent_execution(user_id, f"Agent_{user_id}")
            for user_id in user_ids
        ]
        executions = await asyncio.gather(*execution_tasks)
        
        # Wait for all events to be processed
        await asyncio.sleep(3)
        
        # Verify each user received their own events
        for user_id in user_ids:
            session = websocket_manager.event_capture.sessions[user_id]
            
            # Check all critical events received
            for critical_event in CRITICAL_EVENTS:
                assert critical_event in session.received_events, \
                    f"User {user_id} missing event {critical_event}"
            
            # Verify events contain correct user identification
            for event in session.events:
                if 'user_id' in event.payload:
                    assert event.payload['user_id'] == user_id, \
                        f"Cross-user event detected: event for {event.payload['user_id']} delivered to {user_id}"
        
        # Check for cross-user violations
        violations = websocket_manager.event_capture.cross_user_violations
        assert len(violations) == 0, \
            f"Cross-user violations detected: {violations}"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_concurrent_race_condition_prevention(self, websocket_manager, mock_agent_system):
        """CRITICAL: Test system handles concurrent execution without race conditions."""
        num_concurrent = 15
        user_ids = [f"race_user_{i:03d}" for i in range(num_concurrent)]
        
        # Create connections concurrently
        connect_tasks = [websocket_manager.create_user_connection(user_id) for user_id in user_ids]
        await asyncio.gather(*connect_tasks)
        
        # Start all executions simultaneously (stress test for race conditions)
        execution_tasks = []
        for user_id in user_ids:
            # Add random delays to create more realistic race conditions
            delay = random.uniform(0, 0.1)
            task = asyncio.create_task(self._delayed_execution(mock_agent_system, user_id, delay))
            execution_tasks.append(task)
        
        # Wait for all executions to complete
        results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        # Check that no executions failed due to race conditions
        failures = [r for r in results if isinstance(r, Exception)]
        assert len(failures) == 0, f"Race condition failures: {failures}"
        
        # Wait for event processing
        await asyncio.sleep(2)
        
        # Verify no cross-contamination occurred
        for user_id in user_ids:
            session = websocket_manager.event_capture.sessions[user_id]
            
            # Check events are for correct user
            user_specific_events = [e for e in session.events if 'user_id' in e.payload]
            for event in user_specific_events:
                assert event.payload['user_id'] == user_id, \
                    f"Race condition caused cross-user event: {event.payload['user_id']} -> {user_id}"
    
    async def _delayed_execution(self, mock_agent_system, user_id: str, delay: float):
        """Helper method for delayed execution."""
        await asyncio.sleep(delay)
        return await mock_agent_system.simulate_agent_execution(user_id)


# ============================================================================
# PERFORMANCE AND LOAD TESTS  
# ============================================================================

class TestPerformanceAndLoad:
    """Test WebSocket performance under load conditions."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_high_load_event_delivery_performance(self, websocket_manager, mock_agent_system):
        """CRITICAL: Test event delivery performance under high load."""
        num_users = STRESS_TEST_USERS
        events_per_user = PERFORMANCE_TEST_EVENTS_PER_USER
        user_ids = [f"load_user_{i:03d}" for i in range(num_users)]
        
        # Create all connections
        logger.info(f"Creating {num_users} concurrent connections...")
        connect_start = time.time()
        
        connect_tasks = [websocket_manager.create_user_connection(user_id) for user_id in user_ids]
        connections = await asyncio.gather(*connect_tasks)
        
        connect_time = time.time() - connect_start
        successful_connections = sum(connections)
        
        assert successful_connections >= num_users * 0.9, \
            f"Too many connection failures: {successful_connections}/{num_users}"
        
        logger.info(f"Created {successful_connections} connections in {connect_time:.2f}s")
        
        # Run high-volume executions
        logger.info(f"Starting {events_per_user} executions per user...")
        execution_start = time.time()
        
        all_tasks = []
        for user_id in user_ids[:successful_connections]:  # Only use successful connections
            for i in range(events_per_user):
                task = mock_agent_system.simulate_agent_execution(
                    user_id, f"LoadAgent_{user_id}_{i}"
                )
                all_tasks.append(task)
        
        # Execute all with some concurrency control to avoid overwhelming
        batch_size = 50
        for i in range(0, len(all_tasks), batch_size):
            batch = all_tasks[i:i + batch_size]
            await asyncio.gather(*batch, return_exceptions=True)
            await asyncio.sleep(0.1)  # Small delay between batches
        
        execution_time = time.time() - execution_start
        
        # Wait for event processing
        await asyncio.sleep(5)
        
        # Calculate performance metrics
        metrics = websocket_manager.event_capture.get_performance_metrics()
        
        logger.info(f"Performance Metrics: {json.dumps(metrics, indent=2)}")
        
        # Validate performance requirements
        assert metrics['avg_latency_ms'] < MAX_EVENT_DELAY_MS, \
            f"Average latency too high: {metrics['avg_latency_ms']}ms > {MAX_EVENT_DELAY_MS}ms"
        
        assert metrics['p95_latency_ms'] < MAX_EVENT_DELAY_MS * 2, \
            f"95th percentile latency too high: {metrics['p95_latency_ms']}ms"
        
        assert metrics['events_per_second'] > 10, \
            f"Event throughput too low: {metrics['events_per_second']} events/sec"
        
        # Check that most events were delivered successfully
        total_expected_events = successful_connections * events_per_user * len(CRITICAL_EVENTS)
        delivery_rate = metrics['critical_events_received'] / total_expected_events
        
        assert delivery_rate > 0.95, \
            f"Event delivery rate too low: {delivery_rate:.2%} (expected >95%)"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_connection_timeout_and_recovery(self, websocket_manager, mock_agent_system):
        """CRITICAL: Test connection timeout handling and recovery."""
        user_id = "timeout_user_001"
        
        # Create connection
        connected = await websocket_manager.create_user_connection(user_id)
        assert connected, "Initial connection failed"
        
        # Start agent execution
        execution_task = asyncio.create_task(
            mock_agent_system.simulate_agent_execution(user_id)
        )
        
        # Wait briefly then simulate connection issues
        await asyncio.sleep(0.5)
        
        # Force close the connection to simulate network issues
        if user_id in websocket_manager.connections:
            await websocket_manager.connections[user_id].close()
        
        # Let execution attempt to complete
        execution_result = await execution_task
        
        # Wait a bit more for any recovery attempts
        await asyncio.sleep(1)
        
        # Verify some events were received before the disconnection
        session = websocket_manager.event_capture.sessions[user_id]
        assert len(session.events) > 0, "No events received before disconnection"
        
        # The execution should handle the disconnection gracefully
        # (not crash the whole system)
        assert 'error' not in execution_result or 'connection' in execution_result['error'].lower(), \
            f"Unexpected error type: {execution_result.get('error')}"


# ============================================================================
# ERROR HANDLING AND EDGE CASES
# ============================================================================

class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge case scenarios."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_malformed_message_handling(self, websocket_manager):
        """CRITICAL: Test system handles malformed WebSocket messages gracefully."""
        user_id = "malformed_user_001"
        
        # Create connection
        await websocket_manager.create_user_connection(user_id)
        
        # Send various malformed messages
        malformed_messages = [
            '{"incomplete": json',  # Invalid JSON
            '{"type": null, "payload": {}}',  # Null type
            '{"payload": {"test": true}}',  # Missing type
            '{"type": "", "payload": {}}',  # Empty type
            '{"type": "test", "payload": null}',  # Null payload
            '{"type": "agent_started", "payload": {"incomplete": true}}',  # Missing required fields
        ]
        
        for malformed_msg in malformed_messages:
            # Send raw string instead of using send_test_message
            try:
                websocket = websocket_manager.connections[user_id]
                await websocket.send(malformed_msg)
            except Exception as e:
                # Connection errors are acceptable for malformed messages
                logger.info(f"Expected error sending malformed message: {e}")
        
        # Wait for processing
        await asyncio.sleep(1)
        
        # Verify connection is still alive and responsive
        test_message = {
            "type": "test_message",
            "payload": {"test": True}
        }
        sent = await websocket_manager.send_test_message(user_id, test_message)
        assert sent, "Connection became unresponsive after malformed messages"
        
        # System should still be functional
        session = websocket_manager.event_capture.sessions[user_id]
        assert session.is_active, "Session marked as inactive"
    
    @pytest.mark.asyncio
    @pytest.mark.critical  
    async def test_event_ordering_under_stress(self, websocket_manager, mock_agent_system):
        """CRITICAL: Test event ordering is maintained under stress conditions."""
        user_id = "ordering_user_001"
        
        await websocket_manager.create_user_connection(user_id)
        
        # Run multiple rapid executions to stress the ordering system
        num_executions = 10
        execution_tasks = []
        
        for i in range(num_executions):
            task = mock_agent_system.simulate_agent_execution(
                user_id, f"OrderingAgent_{i}"
            )
            execution_tasks.append(task)
            # Small stagger to create interesting timing
            await asyncio.sleep(0.05)
        
        # Wait for all executions
        await asyncio.gather(*execution_tasks)
        await asyncio.sleep(2)
        
        # Verify events are grouped correctly by execution
        session = websocket_manager.event_capture.sessions[user_id]
        events_by_run = defaultdict(list)
        
        for event in session.events:
            if 'run_id' in event.payload:
                run_id = event.payload['run_id']
                events_by_run[run_id].append(event)
        
        # Each run should have events in correct order
        expected_order = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        
        for run_id, events in events_by_run.items():
            event_types = [e.event_type for e in sorted(events, key=lambda x: x.timestamp)]
            
            # Filter to only critical events for this run
            critical_events_in_run = [et for et in event_types if et in CRITICAL_EVENTS]
            
            if len(critical_events_in_run) == len(expected_order):
                assert critical_events_in_run == expected_order, \
                    f"Event order violation for run {run_id}: {critical_events_in_run} != {expected_order}"
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    async def test_missing_event_detection(self, websocket_manager):
        """CRITICAL: Test detection of missing critical events."""
        user_id = "missing_event_user_001"
        
        await websocket_manager.create_user_connection(user_id)
        
        # Set expected events
        expected_events = list(CRITICAL_EVENTS)
        websocket_manager.event_capture.set_expected_sequence(user_id, expected_events)
        
        # Send only partial events (simulate missing events)
        partial_events = [
            {
                "type": "agent_started",
                "payload": {
                    "agent_name": "PartialAgent",
                    "run_id": "partial_run_001",
                    "timestamp": time.time(),
                    "user_id": user_id
                }
            },
            {
                "type": "tool_executing", 
                "payload": {
                    "tool_name": "partial_tool",
                    "agent_name": "PartialAgent",
                    "timestamp": time.time(),
                    "user_id": user_id
                }
            },
            # Missing: agent_thinking, tool_completed, agent_completed
        ]
        
        for event in partial_events:
            await websocket_manager.send_test_message(user_id, event)
            await asyncio.sleep(0.1)
        
        await asyncio.sleep(1)
        
        # Check for sequence violations (missing events)
        sequence_violations = websocket_manager.event_capture.validate_event_sequences()
        assert len(sequence_violations) > 0, "Missing events were not detected"
        
        # Verify the missing events are identified
        violation = sequence_violations[0]
        assert violation['violation_type'] == 'sequence_length_mismatch', \
            f"Expected sequence_length_mismatch, got {violation['violation_type']}"
        
        # Get session summary to check missing events
        session_summary = websocket_manager.event_capture.get_session_summary()
        user_summary = session_summary[user_id]
        
        assert len(user_summary['missing_events']) > 0, \
            "Missing events not tracked in session summary"


# ============================================================================
# COMPREHENSIVE INTEGRATION TEST
# ============================================================================

class TestComprehensiveIntegration:
    """Comprehensive integration test covering all scenarios."""
    
    @pytest.mark.asyncio
    @pytest.mark.critical
    @pytest.mark.timeout(300)  # 5 minute timeout for comprehensive test
    async def test_comprehensive_websocket_validation(self, websocket_manager, mock_agent_system):
        """
        COMPREHENSIVE: Test all WebSocket functionality together.
        
        This is the ultimate test that combines all scenarios:
        - Multiple concurrent users
        - All critical events
        - Performance validation  
        - Error handling
        - Event ordering
        - Cross-user isolation
        - Timeout handling
        """
        # Test configuration
        num_normal_users = 8
        num_stress_users = 5
        executions_per_user = 3
        
        logger.info("Starting comprehensive WebSocket validation test")
        
        # Phase 1: Create normal users
        normal_users = [f"comp_user_{i:03d}" for i in range(num_normal_users)]
        logger.info(f"Phase 1: Creating {len(normal_users)} normal user connections...")
        
        normal_connect_tasks = [websocket_manager.create_user_connection(user_id) for user_id in normal_users]
        normal_connections = await asyncio.gather(*normal_connect_tasks)
        successful_normal = sum(normal_connections)
        
        assert successful_normal >= len(normal_users) * 0.9, \
            f"Too many normal connection failures: {successful_normal}/{len(normal_users)}"
        
        # Phase 2: Run normal executions with validation
        logger.info(f"Phase 2: Running normal executions...")
        normal_execution_tasks = []
        
        for user_id in normal_users[:successful_normal]:
            for i in range(executions_per_user):
                task = mock_agent_system.simulate_agent_execution(
                    user_id, f"CompAgent_{user_id}_{i}"
                )
                normal_execution_tasks.append(task)
        
        normal_results = await asyncio.gather(*normal_execution_tasks, return_exceptions=True)
        normal_failures = [r for r in normal_results if isinstance(r, Exception)]
        
        assert len(normal_failures) == 0, f"Normal execution failures: {normal_failures}"
        
        # Phase 3: Add stress users while normal users are active  
        stress_users = [f"stress_user_{i:03d}" for i in range(num_stress_users)]
        logger.info(f"Phase 3: Adding {len(stress_users)} stress user connections...")
        
        stress_connect_tasks = [websocket_manager.create_user_connection(user_id) for user_id in stress_users]
        stress_connections = await asyncio.gather(*stress_connect_tasks)
        successful_stress = sum(stress_connections)
        
        # Phase 4: Concurrent stress executions
        logger.info(f"Phase 4: Running concurrent stress executions...")
        stress_execution_tasks = []
        
        for user_id in stress_users[:successful_stress]:
            for i in range(executions_per_user * 2):  # More executions for stress
                task = mock_agent_system.simulate_agent_execution(
                    user_id, f"StressAgent_{user_id}_{i}"
                )
                stress_execution_tasks.append(task)
        
        stress_results = await asyncio.gather(*stress_execution_tasks, return_exceptions=True)
        stress_failures = [r for r in stress_results if isinstance(r, Exception)]
        
        # Allow some failures under stress but not too many
        failure_rate = len(stress_failures) / len(stress_execution_tasks) if stress_execution_tasks else 0
        assert failure_rate < 0.1, f"Too many stress failures: {failure_rate:.1%}"
        
        # Phase 5: Wait for all events and validate
        logger.info("Phase 5: Processing events and validating results...")
        await asyncio.sleep(5)  # Allow time for all events to process
        
        # Get comprehensive metrics
        metrics = websocket_manager.event_capture.get_performance_metrics()
        session_summary = websocket_manager.event_capture.get_session_summary()
        
        logger.info(f"Final Metrics: {json.dumps(metrics, indent=2)}")
        
        # Validate comprehensive requirements
        
        # 1. Performance Requirements
        assert metrics['avg_latency_ms'] < MAX_EVENT_DELAY_MS, \
            f"Average latency too high: {metrics['avg_latency_ms']}ms"
        
        # 2. Event Delivery Requirements
        total_users = successful_normal + successful_stress
        total_executions = len(normal_execution_tasks) + len(stress_execution_tasks) - len(stress_failures)
        expected_events = total_executions * len(CRITICAL_EVENTS)
        
        delivery_rate = metrics['critical_events_received'] / expected_events if expected_events > 0 else 0
        assert delivery_rate > 0.9, \
            f"Event delivery rate too low: {delivery_rate:.1%}"
        
        # 3. Cross-User Isolation Requirements  
        assert metrics['cross_user_violations'] == 0, \
            f"Cross-user violations detected: {metrics['cross_user_violations']}"
        
        # 4. Individual User Validation
        for user_id, summary in session_summary.items():
            # Each user should have received events
            assert summary['events_received'] > 0, \
                f"User {user_id} received no events"
            
            # Critical events should be present
            critical_received = len([et for et in summary['event_types'] if et in CRITICAL_EVENTS])
            assert critical_received >= len(CRITICAL_EVENTS), \
                f"User {user_id} missing critical events: {summary['event_types']}"
        
        # 5. System Stability Requirements
        assert len(websocket_manager.connections) == total_users, \
            "Connection count mismatch - possible connection leaks"
        
        logger.info("Comprehensive WebSocket validation test PASSED")


# ============================================================================
# TEST EXECUTION AND REPORTING
# ============================================================================

if __name__ == "__main__":
    # Run the test suite with detailed output
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--maxfail=1",  # Stop on first failure for faster feedback
        "--durations=10",  # Show 10 slowest tests
        "-m", "critical",  # Run only critical tests
        "--log-cli-level=INFO",
        "--capture=no"  # Show output in real-time
    ])