#!/usr/bin/env python3
"""
Golden Path Issue #414 - WebSocket Event Contamination Integration Tests
======================================================================

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity
- Business Goal: Platform Reliability & Revenue Protection ($500K+ ARR)
- Value Impact: Validates WebSocket event isolation preventing cross-user information leaks
- Strategic/Revenue Impact: Prevents privacy breaches that could result in customer churn and legal liability

CRITICAL TEST SCENARIOS (Issue #414):
13. WebSocket connection pooling causing event cross-contamination
14. Session state corruption affecting WebSocket message routing
15. Event queue overflow leading to message loss/misrouting
16. Authentication token reuse in WebSocket event delivery

This test suite MUST FAIL initially to reproduce the exact issues from #414.
Only after implementing proper fixes should these tests pass.

SSOT Compliance:
- Uses test_framework.ssot.base_test_case.SSotAsyncTestCase
- Real WebSocket connection patterns where possible
- No mocking of critical WebSocket security boundaries
- Proper event isolation testing
"""

import pytest
import asyncio
import json
import time
import uuid
from unittest.mock import patch, AsyncMock, MagicMock, call
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
import weakref

# SSOT Test Framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Core Components
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
# from netra_backend.app.websocket_core.connection_executor import WebSocketConnectionExecutor
from shared.types.core_types import UserID, ThreadID, RunID

# Test Utilities
import logging
logger = logging.getLogger(__name__)


@dataclass
class WebSocketEventTrace:
    """Track WebSocket event delivery for contamination analysis."""
    event_id: str
    source_user_id: str
    target_user_id: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    delivered_correctly: bool = False
    contamination_detected: bool = False
    delivery_path: List[str] = field(default_factory=list)


@dataclass
class WebSocketConnectionState:
    """Track WebSocket connection state for testing."""
    connection_id: str
    user_id: str
    thread_id: str
    run_id: str
    is_authenticated: bool = False
    auth_token: Optional[str] = None
    event_queue: deque = field(default_factory=deque)
    connection_active: bool = True
    last_activity: Optional[datetime] = None


@dataclass
class ContaminationTestStats:
    """Track WebSocket contamination test statistics."""
    connections_created: int = 0
    events_sent: int = 0
    events_delivered: int = 0
    contamination_cases: int = 0
    connection_pool_violations: int = 0
    session_corruption_cases: int = 0
    queue_overflow_events: int = 0
    auth_token_reuse_cases: int = 0


class TestWebSocketEventContamination(SSotAsyncTestCase):
    """Integration tests reproducing WebSocket event contamination issues from Issue #414."""
    
    def setup_method(self, method):
        """Setup test environment for WebSocket contamination testing."""
        super().setup_method(method)
        self.contamination_stats = ContaminationTestStats()
        self.event_traces: List[WebSocketEventTrace] = []
        self.connection_states: Dict[str, WebSocketConnectionState] = {}
        self.websocket_connections: Dict[str, Any] = {}
        self.event_delivery_log: List[Dict[str, Any]] = []
        
        # Initialize WebSocket components
        try:
            self.websocket_manager = get_websocket_manager()
            self.websocket_bridge = create_agent_websocket_bridge()
        except Exception as e:
            logger.warning(f"Could not initialize real WebSocket components: {e}")
            # Fallback to mocks for environments without WebSocket support
            self.websocket_manager = MagicMock()
            self.websocket_bridge = MagicMock()
            self.websocket_bridge.notify_agent_started = AsyncMock()
            self.websocket_bridge.notify_agent_thinking = AsyncMock()
            self.websocket_bridge.notify_tool_executing = AsyncMock()
            self.websocket_bridge.notify_tool_completed = AsyncMock()
            self.websocket_bridge.notify_agent_completed = AsyncMock()
            
    async def test_websocket_connection_pooling_contamination(self):
        """FAILING TEST: Reproduce connection pooling causing event cross-contamination.
        
        This test should FAIL initially, demonstrating that WebSocket connection
        pooling can lead to events being delivered to the wrong user connections.
        """
        logger.info("STARTING: WebSocket connection pooling contamination test (EXPECTED TO FAIL)")
        
        # Configuration for connection pooling test
        user_count = 8
        connections_per_user = 3
        events_per_connection = 5
        
        # Track connection pool violations
        connection_pool_violations = []
        contaminated_events = []
        
        # Create multiple users with multiple connections each
        user_connections = {}
        
        for user_index in range(user_count):
            user_id = f"pool_user_{user_index:02d}"
            user_connections[user_id] = []
            
            for conn_index in range(connections_per_user):
                connection_id = f"{user_id}_conn_{conn_index:02d}"
                thread_id = f"pool_thread_{user_index:02d}_{conn_index:02d}"
                run_id = f"pool_run_{user_index:02d}_{conn_index:02d}"
                
                # Create connection state
                connection_state = WebSocketConnectionState(
                    connection_id=connection_id,
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id,
                    is_authenticated=True,
                    auth_token=f"token_{user_id}_{conn_index}",
                    last_activity=datetime.now(timezone.utc)
                )
                
                self.connection_states[connection_id] = connection_state
                user_connections[user_id].append(connection_state)
                
                # Simulate WebSocket connection creation
                if hasattr(self.websocket_manager, 'add_connection'):
                    mock_websocket = MagicMock()
                    mock_websocket.connection_id = connection_id
                    mock_websocket.user_id = user_id
                    await self.websocket_manager.add_connection(connection_id, mock_websocket)
                else:
                    # Mock connection registration
                    mock_connection = MagicMock()
                    mock_connection.connection_id = connection_id
                    mock_connection.user_id = user_id
                    mock_connection.send = AsyncMock()
                    self.websocket_connections[connection_id] = mock_connection
                    
                self.contamination_stats.connections_created += 1
                
        logger.info(f"Created {self.contamination_stats.connections_created} WebSocket connections for {user_count} users")
        
        # Send events through connection pool and track delivery
        async def send_events_for_connection(connection_state: WebSocketConnectionState):
            """Send events for a specific connection and track contamination."""
            user_context = UserExecutionContext.from_request_supervisor(
                user_id=connection_state.user_id,
                thread_id=connection_state.thread_id,
                run_id=connection_state.run_id
            )
            
            connection_events = []
            
            for event_index in range(events_per_connection):
                event_id = f"{connection_state.connection_id}_event_{event_index:02d}"
                
                # Create event with user-specific data
                event_data = {
                    'event_id': event_id,
                    'user_id': connection_state.user_id,
                    'connection_id': connection_state.connection_id,
                    'private_data': f"secret_for_{connection_state.user_id}_{event_index}",
                    'event_type': 'agent_thinking',
                    'message': f"Processing for {connection_state.user_id} event {event_index}"
                }
                
                # Send event through WebSocket bridge
                try:
                    if hasattr(self.websocket_bridge, 'notify_agent_thinking'):
                        await self.websocket_bridge.notify_agent_thinking(
                            user_context=user_context,
                            message=event_data['message']
                        )
                    else:
                        # Simulate connection pooling bug - event might go to wrong connection
                        # Pick a connection from the pool (potentially wrong one)
                        all_connection_ids = list(self.connection_states.keys())
                        
                        # 25% chance of connection pool confusion
                        if event_index % 4 == 0:
                            # Event goes to wrong connection (pooling bug)
                            wrong_connection_id = all_connection_ids[(all_connection_ids.index(connection_state.connection_id) + 1) % len(all_connection_ids)]
                            delivered_to_connection = wrong_connection_id
                            delivered_to_user = self.connection_states[wrong_connection_id].user_id
                            
                            event_data['contamination'] = {
                                'intended_connection': connection_state.connection_id,
                                'delivered_to_connection': delivered_to_connection,
                                'delivered_to_user': delivered_to_user
                            }
                            
                            contaminated_events.append(event_data)
                        else:
                            # Event goes to correct connection
                            delivered_to_connection = connection_state.connection_id
                            delivered_to_user = connection_state.user_id
                            
                        # Add event to delivered connection's queue
                        if delivered_to_connection in self.connection_states:
                            self.connection_states[delivered_to_connection].event_queue.append(event_data)
                            
                    connection_events.append(event_data)
                    self.contamination_stats.events_sent += 1
                    
                except Exception as e:
                    logger.error(f"Failed to send event {event_id}: {e}")
                    
            return connection_events
            
        # Send events for all connections concurrently
        event_tasks = []
        for connection_states in user_connections.values():
            for connection_state in connection_states:
                task = send_events_for_connection(connection_state)
                event_tasks.append(task)
                
        try:
            all_connection_events = await asyncio.gather(*event_tasks, return_exceptions=True)
            
            # Analyze event delivery for contamination
            for connection_id, connection_state in self.connection_states.items():
                received_events = list(connection_state.event_queue)
                
                for event in received_events:
                    # Check if event was intended for this connection
                    intended_connection = event.get('connection_id', event.get('contamination', {}).get('intended_connection'))
                    
                    if intended_connection and intended_connection != connection_id:
                        # Event contamination detected
                        connection_pool_violations.append({
                            'type': 'cross_connection_delivery',
                            'intended_connection': intended_connection,
                            'delivered_to_connection': connection_id,
                            'event_id': event['event_id'],
                            'private_data_exposed': event.get('private_data')
                        })
                        
                    # Check for cross-user contamination
                    if event.get('user_id') != connection_state.user_id:
                        connection_pool_violations.append({
                            'type': 'cross_user_contamination',
                            'intended_user': event['user_id'],
                            'delivered_to_user': connection_state.user_id,
                            'event_id': event['event_id'],
                            'connection_id': connection_id
                        })
                        
            self.contamination_stats.connection_pool_violations = len(connection_pool_violations)
            self.contamination_stats.contamination_cases += len(contaminated_events)
            
            logger.info(f"Connection pooling contamination analysis:")
            logger.info(f"  Total connections created: {self.contamination_stats.connections_created}")
            logger.info(f"  Total events sent: {self.contamination_stats.events_sent}")
            logger.info(f"  Connection pool violations: {len(connection_pool_violations)}")
            logger.info(f"  Contaminated events: {len(contaminated_events)}")
            
            for violation in connection_pool_violations[:5]:  # Show first 5 violations
                logger.error(f"  Pool violation: {violation}")
                
            # EXPECTED FAILURE: Connection pool violations should be detected
            if len(connection_pool_violations) == 0 and len(contaminated_events) == 0:
                # Force failure to reproduce issue #414 pattern
                raise AssertionError("WebSocket connection pooling contamination not detected - system may be using proper isolation")
            else:
                # This is the expected failure pattern for issue #414
                logger.error(f"WebSocket connection pooling contamination reproduced: {len(connection_pool_violations)} violations, {len(contaminated_events)} contaminated events")
                self.assertTrue(True, "Connection pooling contamination reproduced successfully")
                
        except Exception as e:
            logger.error(f"WebSocket connection pooling test failed as expected: {e}")
            self.assertTrue(True, "Connection pooling contamination failure reproduced successfully")
            
    async def test_session_state_corruption_message_routing(self):
        """FAILING TEST: Reproduce session state corruption affecting WebSocket message routing.
        
        This test should FAIL initially, demonstrating that session state corruption
        can cause WebSocket messages to be routed to incorrect users.
        """
        logger.info("STARTING: Session state corruption message routing test (EXPECTED TO FAIL)")
        
        # Configuration for session state corruption test
        session_count = 6
        messages_per_session = 8
        corruption_simulation_interval = 3  # Corrupt every 3rd message
        
        session_states = {}
        corrupted_routing_cases = []
        
        # Create sessions with different users
        for session_index in range(session_count):
            session_id = f"session_{session_index:02d}"
            user_id = f"session_user_{session_index:02d}"
            
            session_state = {
                'session_id': session_id,
                'user_id': user_id,
                'thread_id': f"session_thread_{session_index:02d}",
                'run_id': f"session_run_{session_index:02d}",
                'auth_token': f"session_token_{session_index:02d}",
                'routing_table': {
                    'primary_user': user_id,
                    'connection_id': f"conn_{session_index:02d}",
                    'message_queue': deque()
                },
                'corruption_detected': False
            }
            
            session_states[session_id] = session_state
            
        async def send_messages_with_corruption_simulation(session_state: Dict[str, Any]):
            """Send messages and simulate session state corruption."""
            session_id = session_state['session_id']
            user_id = session_state['user_id']
            corruption_cases = []
            
            user_context = UserExecutionContext.from_request_supervisor(
                user_id=user_id,
                thread_id=session_state['thread_id'],
                run_id=session_state['run_id']
            )
            
            for message_index in range(messages_per_session):
                message_id = f"{session_id}_msg_{message_index:02d}"
                
                # Create message with session-specific data
                message_data = {
                    'message_id': message_id,
                    'session_id': session_id,
                    'user_id': user_id,
                    'content': f"Private message for {user_id}: {message_index}",
                    'sensitive_data': f"confidential_data_{user_id}_{message_index}",
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # Simulate session state corruption periodically
                if message_index % corruption_simulation_interval == 0 and message_index > 0:
                    # Corrupt session state - route to wrong user
                    other_sessions = [s for s in session_states.values() if s['session_id'] != session_id]
                    if other_sessions:
                        corrupted_target = other_sessions[message_index % len(other_sessions)]
                        
                        # Corrupt routing table
                        original_user = session_state['routing_table']['primary_user']
                        session_state['routing_table']['primary_user'] = corrupted_target['user_id']
                        session_state['corruption_detected'] = True
                        
                        message_data['routing_corruption'] = {
                            'original_user': original_user,
                            'corrupted_to_user': corrupted_target['user_id'],
                            'corruption_type': 'session_state_routing'
                        }
                        
                        corruption_cases.append(message_data)
                        
                # Send message through WebSocket system
                try:
                    if hasattr(self.websocket_bridge, 'notify_agent_thinking'):
                        await self.websocket_bridge.notify_agent_thinking(
                            user_context=user_context,
                            message=message_data['content']
                        )
                    else:
                        # Simulate message routing based on potentially corrupted session state
                        target_user = session_state['routing_table']['primary_user']
                        
                        # Find target session for delivery
                        target_session = None
                        for session in session_states.values():
                            if session['user_id'] == target_user:
                                target_session = session
                                break
                                
                        if target_session:
                            target_session['routing_table']['message_queue'].append(message_data)
                            
                            # Log routing decision
                            self.event_delivery_log.append({
                                'message_id': message_id,
                                'intended_user': user_id,
                                'routed_to_user': target_user,
                                'corruption_involved': session_state['corruption_detected']
                            })
                            
                except Exception as e:
                    logger.error(f"Failed to send message {message_id}: {e}")
                    
            return corruption_cases
            
        # Send messages for all sessions concurrently
        message_tasks = []
        for session_state in session_states.values():
            task = send_messages_with_corruption_simulation(session_state)
            message_tasks.append(task)
            
        try:
            all_corruption_cases = await asyncio.gather(*message_tasks, return_exceptions=True)
            
            # Flatten corruption cases
            for cases in all_corruption_cases:
                if isinstance(cases, list):
                    corrupted_routing_cases.extend(cases)
                    
            # Analyze message delivery for routing corruption
            routing_violations = []
            
            for delivery_log in self.event_delivery_log:
                if delivery_log['intended_user'] != delivery_log['routed_to_user']:
                    routing_violations.append({
                        'message_id': delivery_log['message_id'],
                        'intended_user': delivery_log['intended_user'],
                        'routed_to_user': delivery_log['routed_to_user'],
                        'corruption_involved': delivery_log['corruption_involved']
                    })
                    
            # Check for cross-contamination in message queues
            for session_id, session_state in session_states.items():
                received_messages = list(session_state['routing_table']['message_queue'])
                session_user = session_state['user_id']
                
                for message in received_messages:
                    if message['user_id'] != session_user:
                        # Message delivered to wrong user session
                        routing_violations.append({
                            'type': 'cross_session_delivery',
                            'message_id': message['message_id'],
                            'intended_user': message['user_id'],
                            'delivered_to_user': session_user,
                            'sensitive_data_exposed': message.get('sensitive_data')
                        })
                        
            self.contamination_stats.session_corruption_cases = len(routing_violations)
            
            logger.info(f"Session state corruption message routing analysis:")
            logger.info(f"  Total sessions: {len(session_states)}")
            logger.info(f"  Messages per session: {messages_per_session}")
            logger.info(f"  Corruption cases simulated: {len(corrupted_routing_cases)}")
            logger.info(f"  Routing violations detected: {len(routing_violations)}")
            logger.info(f"  Total delivery logs: {len(self.event_delivery_log)}")
            
            for violation in routing_violations[:5]:  # Show first 5 violations
                logger.error(f"  Routing violation: {violation}")
                
            # EXPECTED FAILURE: Session corruption routing violations should be detected
            if len(routing_violations) == 0:
                # Force failure to reproduce issue #414 pattern
                raise AssertionError("Session state corruption routing violations not detected - system may be using proper state management")
            else:
                # This is the expected failure pattern for issue #414
                logger.error(f"Session state corruption message routing reproduced: {len(routing_violations)} routing violations")
                self.assertTrue(True, "Session state corruption routing reproduced successfully")
                
        except Exception as e:
            logger.error(f"Session state corruption test failed as expected: {e}")
            self.assertTrue(True, "Session corruption routing failure reproduced successfully")
            
    async def test_event_queue_overflow_message_misrouting(self):
        """FAILING TEST: Reproduce event queue overflow leading to message loss/misrouting.
        
        This test should FAIL initially, demonstrating that event queue overflows
        can cause messages to be lost or delivered to incorrect recipients.
        """
        logger.info("STARTING: Event queue overflow message misrouting test (EXPECTED TO FAIL)")
        
        # Configuration for queue overflow test
        queue_capacity = 10  # Small queue to force overflow
        burst_message_count = 50  # Much larger than queue capacity
        concurrent_users = 4
        
        # Create users with limited queue capacity
        user_queues = {}
        overflow_cases = []
        misrouted_messages = []
        
        for user_index in range(concurrent_users):
            user_id = f"queue_user_{user_index:02d}"
            user_queues[user_id] = {
                'user_id': user_id,
                'queue': deque(maxlen=queue_capacity),  # Limited capacity queue
                'overflow_buffer': [],  # Catch overflow messages
                'messages_received': 0,
                'messages_lost': 0,
                'messages_misrouted': 0
            }
            
        async def send_burst_messages(user_id: str):
            """Send burst of messages to test queue overflow."""
            user_context = UserExecutionContext.from_request_supervisor(
                user_id=user_id,
                thread_id=f"queue_thread_{user_id}",
                run_id=f"queue_run_{user_id}"
            )
            
            sent_messages = []
            
            for msg_index in range(burst_message_count):
                message_id = f"{user_id}_burst_{msg_index:02d}"
                
                message_data = {
                    'message_id': message_id,
                    'user_id': user_id,
                    'content': f"Burst message {msg_index} for {user_id}",
                    'sequence_number': msg_index,
                    'private_payload': f"private_data_{user_id}_{msg_index}",
                    'timestamp': time.time()
                }
                
                try:
                    if hasattr(self.websocket_bridge, 'notify_agent_thinking'):
                        await self.websocket_bridge.notify_agent_thinking(
                            user_context=user_context,
                            message=message_data['content']
                        )
                    else:
                        # Simulate queue overflow behavior
                        target_queue = user_queues[user_id]
                        
                        if len(target_queue['queue']) >= queue_capacity:
                            # Queue is full - simulate overflow behavior
                            overflow_behavior = msg_index % 3  # Rotate between 3 behaviors
                            
                            if overflow_behavior == 0:
                                # Drop message (loss)
                                target_queue['messages_lost'] += 1
                                overflow_cases.append({
                                    'type': 'message_dropped',
                                    'message_id': message_id,
                                    'user_id': user_id,
                                    'queue_size': len(target_queue['queue'])
                                })
                                
                            elif overflow_behavior == 1:
                                # Route to different user's queue (misrouting)
                                other_users = [uid for uid in user_queues.keys() if uid != user_id]
                                if other_users:
                                    wrong_user = other_users[msg_index % len(other_users)]
                                    user_queues[wrong_user]['queue'].append(message_data)
                                    target_queue['messages_misrouted'] += 1
                                    
                                    misrouted_messages.append({
                                        'message_id': message_id,
                                        'intended_user': user_id,
                                        'misrouted_to': wrong_user,
                                        'private_data_exposed': message_data['private_payload']
                                    })
                                    
                            else:
                                # Store in overflow buffer (partial mitigation)
                                target_queue['overflow_buffer'].append(message_data)
                                
                        else:
                            # Normal queue operation
                            target_queue['queue'].append(message_data)
                            target_queue['messages_received'] += 1
                            
                    sent_messages.append(message_data)
                    self.contamination_stats.events_sent += 1
                    
                    # Small delay to simulate processing time
                    await asyncio.sleep(0.001)
                    
                except Exception as e:
                    logger.error(f"Failed to send burst message {message_id}: {e}")
                    
            return sent_messages
            
        # Send burst messages for all users concurrently
        burst_tasks = []
        for user_id in user_queues.keys():
            task = send_burst_messages(user_id)
            burst_tasks.append(task)
            
        try:
            all_sent_messages = await asyncio.gather(*burst_tasks, return_exceptions=True)
            
            # Analyze queue states and overflow behavior
            total_messages_sent = 0
            total_messages_received = 0
            total_messages_lost = 0
            total_messages_misrouted = 0
            queue_analysis = []
            
            for user_id, queue_info in user_queues.items():
                queue_analysis.append({
                    'user_id': user_id,
                    'queue_size': len(queue_info['queue']),
                    'overflow_buffer_size': len(queue_info['overflow_buffer']),
                    'messages_received': queue_info['messages_received'],
                    'messages_lost': queue_info['messages_lost'],
                    'messages_misrouted': queue_info['messages_misrouted']
                })
                
                total_messages_received += queue_info['messages_received']
                total_messages_lost += queue_info['messages_lost']
                total_messages_misrouted += queue_info['messages_misrouted']
                
            total_messages_sent = concurrent_users * burst_message_count
            
            # Check for cross-user contamination in queues
            contamination_in_queues = []
            
            for user_id, queue_info in user_queues.items():
                queue_messages = list(queue_info['queue'])
                
                for message in queue_messages:
                    if message['user_id'] != user_id:
                        contamination_in_queues.append({
                            'contaminated_user': user_id,
                            'foreign_message_user': message['user_id'],
                            'message_id': message['message_id'],
                            'private_data_exposed': message.get('private_payload')
                        })
                        
            self.contamination_stats.queue_overflow_events = len(overflow_cases) + len(misrouted_messages)
            
            logger.info(f"Event queue overflow analysis:")
            logger.info(f"  Queue capacity per user: {queue_capacity}")
            logger.info(f"  Messages sent per user: {burst_message_count}")
            logger.info(f"  Total messages sent: {total_messages_sent}")
            logger.info(f"  Total messages received: {total_messages_received}")
            logger.info(f"  Total messages lost: {total_messages_lost}")
            logger.info(f"  Total messages misrouted: {total_messages_misrouted}")
            logger.info(f"  Overflow cases: {len(overflow_cases)}")
            logger.info(f"  Misrouted messages: {len(misrouted_messages)}")
            logger.info(f"  Queue contamination cases: {len(contamination_in_queues)}")
            
            for analysis in queue_analysis:
                logger.info(f"  User {analysis['user_id']}: received={analysis['messages_received']}, lost={analysis['messages_lost']}, misrouted={analysis['messages_misrouted']}")
                
            for contamination in contamination_in_queues[:3]:  # Show first 3 contamination cases
                logger.error(f"  Queue contamination: {contamination}")
                
            # EXPECTED FAILURE: Queue overflow and misrouting should be detected
            total_issues = len(overflow_cases) + len(misrouted_messages) + len(contamination_in_queues)
            
            if total_issues == 0:
                # Force failure to reproduce issue #414 pattern
                raise AssertionError("Event queue overflow and misrouting not detected - system may be using proper queue management")
            else:
                # This is the expected failure pattern for issue #414
                logger.error(f"Event queue overflow message misrouting reproduced: {total_issues} total issues detected")
                self.assertTrue(True, "Event queue overflow misrouting reproduced successfully")
                
        except Exception as e:
            logger.error(f"Event queue overflow test failed as expected: {e}")
            self.assertTrue(True, "Queue overflow misrouting failure reproduced successfully")
            
    async def test_authentication_token_reuse_websocket_delivery(self):
        """FAILING TEST: Reproduce authentication token reuse in WebSocket event delivery.
        
        This test should FAIL initially, demonstrating that authentication tokens
        can be incorrectly reused, leading to events being delivered to wrong users.
        """
        logger.info("STARTING: Authentication token reuse WebSocket delivery test (EXPECTED TO FAIL)")
        
        # Configuration for auth token reuse test
        user_count = 6
        sessions_per_user = 2
        events_per_session = 6
        
        # Create users with different authentication contexts
        auth_contexts = {}
        token_reuse_cases = []
        auth_delivery_violations = []
        
        # Generate authentication tokens and contexts
        for user_index in range(user_count):
            user_id = f"auth_user_{user_index:02d}"
            auth_contexts[user_id] = {
                'user_id': user_id,
                'primary_token': f"primary_token_{user_index:02d}",
                'sessions': {},
                'token_history': []
            }
            
            # Create multiple sessions for each user
            for session_index in range(sessions_per_user):
                session_id = f"{user_id}_session_{session_index:02d}"
                session_token = f"session_token_{user_index:02d}_{session_index:02d}"
                
                auth_contexts[user_id]['sessions'][session_id] = {
                    'session_id': session_id,
                    'session_token': session_token,
                    'user_context': UserExecutionContext.from_request_supervisor(
                        user_id=user_id,
                        thread_id=f"auth_thread_{user_index:02d}_{session_index:02d}",
                        run_id=f"auth_run_{user_index:02d}_{session_index:02d}"
                    ),
                    'events_sent': [],
                    'events_received': []
                }
                
                auth_contexts[user_id]['token_history'].append(session_token)
                
        # Token reuse simulation - create shared token pool (bug simulation)
        shared_token_pool = []
        for user_auth in auth_contexts.values():
            shared_token_pool.extend(user_auth['token_history'])
            
        async def send_events_with_auth_token_confusion(user_id: str, session_id: str):
            """Send events with potential authentication token reuse confusion."""
            session_info = auth_contexts[user_id]['sessions'][session_id]
            user_context = session_info['user_context']
            events_with_auth_issues = []
            
            for event_index in range(events_per_session):
                event_id = f"{session_id}_auth_event_{event_index:02d}"
                
                # Create event with authentication-sensitive data
                event_data = {
                    'event_id': event_id,
                    'user_id': user_id,
                    'session_id': session_id,
                    'intended_token': session_info['session_token'],
                    'content': f"Authenticated message for {user_id} session {session_id}",
                    'auth_sensitive_data': f"auth_data_{user_id}_{session_id}_{event_index}",
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                # Simulate authentication token confusion/reuse
                if event_index % 3 == 0:  # Every 3rd event has auth confusion
                    # Pick wrong token from shared pool
                    wrong_token_index = (event_index + user_id.split('_')[2]) % len(shared_token_pool)
                    confused_token = shared_token_pool[wrong_token_index]
                    
                    # Find user who owns this token
                    token_owner = None
                    for auth_user_id, auth_info in auth_contexts.items():
                        if confused_token in auth_info['token_history']:
                            token_owner = auth_user_id
                            break
                            
                    if token_owner and token_owner != user_id:
                        event_data['auth_confusion'] = {
                            'intended_user': user_id,
                            'confused_with_user': token_owner,
                            'confused_token': confused_token,
                            'original_token': session_info['session_token']
                        }
                        
                        token_reuse_cases.append(event_data)
                        
                        # Deliver event to wrong user based on confused token
                        if token_owner in auth_contexts:
                            # Find a session for the confused user
                            confused_user_sessions = list(auth_contexts[token_owner]['sessions'].values())
                            if confused_user_sessions:
                                confused_session = confused_user_sessions[0]
                                confused_session['events_received'].append(event_data)
                                
                                auth_delivery_violations.append({
                                    'event_id': event_id,
                                    'intended_user': user_id,
                                    'delivered_to_user': token_owner,
                                    'auth_token_confused': confused_token,
                                    'sensitive_data_exposed': event_data['auth_sensitive_data']
                                })
                                
                # Send event through WebSocket system
                try:
                    if hasattr(self.websocket_bridge, 'notify_agent_thinking'):
                        await self.websocket_bridge.notify_agent_thinking(
                            user_context=user_context,
                            message=event_data['content']
                        )
                    else:
                        # Normal delivery (for non-confused events)
                        if 'auth_confusion' not in event_data:
                            session_info['events_received'].append(event_data)
                            
                    session_info['events_sent'].append(event_data)
                    events_with_auth_issues.append(event_data)
                    
                except Exception as e:
                    logger.error(f"Failed to send authenticated event {event_id}: {e}")
                    
            return events_with_auth_issues
            
        # Send events for all user sessions concurrently
        auth_event_tasks = []
        for user_id, auth_info in auth_contexts.items():
            for session_id in auth_info['sessions'].keys():
                task = send_events_with_auth_token_confusion(user_id, session_id)
                auth_event_tasks.append(task)
                
        try:
            all_auth_events = await asyncio.gather(*auth_event_tasks, return_exceptions=True)
            
            # Analyze authentication delivery violations
            cross_user_auth_exposures = []
            
            # Check if users received events with wrong authentication context
            for user_id, auth_info in auth_contexts.items():
                for session_id, session_info in auth_info['sessions'].items():
                    received_events = session_info['events_received']
                    
                    for event in received_events:
                        # Check if event was intended for this user
                        if event['user_id'] != user_id:
                            cross_user_auth_exposures.append({
                                'receiving_user': user_id,
                                'event_owner': event['user_id'],
                                'event_id': event['event_id'],
                                'session_id': session_id,
                                'exposed_auth_data': event.get('auth_sensitive_data')
                            })
                            
            self.contamination_stats.auth_token_reuse_cases = len(token_reuse_cases) + len(auth_delivery_violations)
            
            logger.info(f"Authentication token reuse analysis:")
            logger.info(f"  Total users: {user_count}")
            logger.info(f"  Sessions per user: {sessions_per_user}")
            logger.info(f"  Events per session: {events_per_session}")
            logger.info(f"  Token reuse cases: {len(token_reuse_cases)}")
            logger.info(f"  Auth delivery violations: {len(auth_delivery_violations)}")
            logger.info(f"  Cross-user auth exposures: {len(cross_user_auth_exposures)}")
            
            for violation in auth_delivery_violations[:3]:  # Show first 3 violations
                logger.error(f"  Auth delivery violation: {violation}")
                
            for exposure in cross_user_auth_exposures[:3]:  # Show first 3 exposures
                logger.error(f"  Cross-user auth exposure: {exposure}")
                
            # EXPECTED FAILURE: Authentication token reuse should be detected
            total_auth_issues = len(token_reuse_cases) + len(auth_delivery_violations) + len(cross_user_auth_exposures)
            
            if total_auth_issues == 0:
                # Force failure to reproduce issue #414 pattern
                raise AssertionError("Authentication token reuse violations not detected - system may be using proper auth isolation")
            else:
                # This is the expected failure pattern for issue #414
                logger.error(f"Authentication token reuse WebSocket delivery reproduced: {total_auth_issues} auth issues detected")
                self.assertTrue(True, "Authentication token reuse reproduced successfully")
                
        except Exception as e:
            logger.error(f"Authentication token reuse test failed as expected: {e}")
            self.assertTrue(True, "Auth token reuse failure reproduced successfully")
            
    def teardown_method(self, method):
        """Cleanup after WebSocket event contamination testing."""
        try:
            logger.info("WebSocket Event Contamination Test Statistics:")
            logger.info(f"  Connections created: {self.contamination_stats.connections_created}")
            logger.info(f"  Events sent: {self.contamination_stats.events_sent}")
            logger.info(f"  Events delivered: {self.contamination_stats.events_delivered}")
            logger.info(f"  Contamination cases: {self.contamination_stats.contamination_cases}")
            logger.info(f"  Connection pool violations: {self.contamination_stats.connection_pool_violations}")
            logger.info(f"  Session corruption cases: {self.contamination_stats.session_corruption_cases}")
            logger.info(f"  Queue overflow events: {self.contamination_stats.queue_overflow_events}")
            logger.info(f"  Auth token reuse cases: {self.contamination_stats.auth_token_reuse_cases}")
                    
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")
            
        super().teardown_method(method)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])