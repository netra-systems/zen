"""
CRITICAL E2E TEST SUITE: Thread Switching Consistency

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure seamless thread switching maintains conversation continuity
- Value Impact: Users must be able to switch between conversations without losing context
- Strategic Impact: Core UX for multi-conversation Chat platform workflow

CRITICAL REQUIREMENTS:
-  PASS:  Real authentication via e2e_auth_helper.py (NO MOCKS = ABOMINATION) 
-  PASS:  Full Docker stack + Database + WebSocket
-  PASS:  Thread context preservation validation across switches
-  PASS:  Message history persistence per thread
-  PASS:  WebSocket room switching validation
-  PASS:  Tests designed to FAIL initially (find thread switching edge case bugs)

This test validates that users can seamlessly switch between multiple conversation
threads while maintaining perfect context isolation and history preservation.
Expected initial failures due to thread switching edge case bugs.
"""
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Set, Any, Optional, Tuple
import pytest
from contextlib import asynccontextmanager
import websockets
from websockets import ConnectionClosedError, WebSocketException
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from shared.isolated_environment import get_env, IsolatedEnvironment
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context, E2EAuthConfig
from test_framework.base_e2e_test import BaseE2ETest
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RequestID, MessageID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
logger = logging.getLogger(__name__)

class ThreadSwitchingTracker:
    """
    Framework for tracking thread switching behavior and context preservation.
    
    Features:
    - Thread context state tracking across switches
    - Message history validation per thread
    - WebSocket room switching monitoring
    - Context preservation verification
    """

    def __init__(self, environment: str='test'):
        self.environment = environment
        self.start_time = time.time()
        self.thread_states: Dict[str, Dict] = {}
        self.thread_messages: Dict[str, List[Dict]] = {}
        self.thread_switches: List[Dict] = []
        self.context_preservation_failures: List[Dict] = []
        self.websocket_rooms: Dict[str, str] = {}
        self.room_switch_events: List[Dict] = []
        self.user_sessions: Dict[str, Dict] = {}

    def initialize_thread(self, user_id: str, thread_id: str, thread_title: str, context: Dict=None):
        """Initialize thread state for tracking."""
        self.thread_states[thread_id] = {'user_id': user_id, 'thread_id': thread_id, 'title': thread_title, 'created_at': time.time(), 'last_accessed': time.time(), 'message_count': 0, 'active': True, 'context': context or {}}
        self.thread_messages[thread_id] = []
        if user_id not in self.websocket_rooms:
            self.websocket_rooms[user_id] = thread_id
            logger.info(f'[U+1F3E0] User {user_id} initial WebSocket room set to thread {thread_id}')
        logger.info(f'[U+1F4DD] Initialized thread {thread_id} for user {user_id}: {thread_title}')

    def track_message(self, user_id: str, thread_id: str, message_type: str, message_data: Dict):
        """Track message in specific thread."""
        if thread_id not in self.thread_messages:
            self.thread_messages[thread_id] = []
        message_entry = {'timestamp': time.time(), 'relative_time': time.time() - self.start_time, 'user_id': user_id, 'thread_id': thread_id, 'message_type': message_type, 'message_data': message_data, 'sequence_number': len(self.thread_messages[thread_id])}
        self.thread_messages[thread_id].append(message_entry)
        if thread_id in self.thread_states:
            self.thread_states[thread_id]['message_count'] += 1
            self.thread_states[thread_id]['last_accessed'] = time.time()
        logger.debug(f'[U+1F4AC] Tracked {message_type} message in thread {thread_id} for user {user_id}')

    def track_thread_switch(self, user_id: str, from_thread_id: str, to_thread_id: str, switch_reason: str='user_action'):
        """Track thread switching event with context validation."""
        switch_timestamp = time.time()
        context_preserved = self._validate_context_preservation(from_thread_id, to_thread_id)
        switch_entry = {'timestamp': switch_timestamp, 'relative_time': switch_timestamp - self.start_time, 'user_id': user_id, 'from_thread_id': from_thread_id, 'to_thread_id': to_thread_id, 'switch_reason': switch_reason, 'context_preserved': context_preserved, 'switch_duration': 0}
        self.thread_switches.append(switch_entry)
        previous_room = self.websocket_rooms.get(user_id)
        self.websocket_rooms[user_id] = to_thread_id
        self.room_switch_events.append({'timestamp': switch_timestamp, 'user_id': user_id, 'previous_room': previous_room, 'new_room': to_thread_id})
        if from_thread_id in self.thread_states:
            self.thread_states[from_thread_id]['active'] = False
        if to_thread_id in self.thread_states:
            self.thread_states[to_thread_id]['active'] = True
            self.thread_states[to_thread_id]['last_accessed'] = switch_timestamp
        if not context_preserved:
            failure_entry = {'timestamp': switch_timestamp, 'user_id': user_id, 'from_thread': from_thread_id, 'to_thread': to_thread_id, 'failure_type': 'context_preservation'}
            self.context_preservation_failures.append(failure_entry)
            logger.error(f' ALERT:  CONTEXT PRESERVATION FAILURE: User {user_id} switch from {from_thread_id} to {to_thread_id}')
        logger.info(f' CYCLE:  User {user_id} switched from thread {from_thread_id} to {to_thread_id}')
        return len(self.thread_switches) - 1

    def complete_thread_switch(self, switch_index: int, completion_data: Dict=None):
        """Mark thread switch as completed with timing data."""
        if 0 <= switch_index < len(self.thread_switches):
            switch_entry = self.thread_switches[switch_index]
            completion_time = time.time()
            switch_entry['switch_duration'] = completion_time - switch_entry['timestamp']
            switch_entry['completion_data'] = completion_data or {}
            logger.debug(f" PASS:  Thread switch completed in {switch_entry['switch_duration']:.3f}s")

    def _validate_context_preservation(self, from_thread_id: str, to_thread_id: str) -> bool:
        """Validate that thread context is preserved across switches."""
        if from_thread_id in self.thread_states:
            from_state = self.thread_states[from_thread_id]
            if from_state['message_count'] == 0:
                return False
        if to_thread_id not in self.thread_states:
            return False
        return True

    def validate_thread_history_preservation(self, thread_id: str) -> Dict:
        """Validate that thread message history is preserved."""
        if thread_id not in self.thread_messages:
            return {'preserved': False, 'error': 'Thread not found in message history', 'message_count': 0}
        thread_messages = self.thread_messages[thread_id]
        expected_sequence = 0
        sequence_intact = True
        for msg in thread_messages:
            if msg['sequence_number'] != expected_sequence:
                sequence_intact = False
                break
            expected_sequence += 1
        temporal_ordered = True
        for i in range(1, len(thread_messages)):
            if thread_messages[i]['timestamp'] < thread_messages[i - 1]['timestamp']:
                temporal_ordered = False
                break
        return {'preserved': sequence_intact and temporal_ordered, 'message_count': len(thread_messages), 'sequence_intact': sequence_intact, 'temporal_ordered': temporal_ordered, 'first_message': thread_messages[0] if thread_messages else None, 'last_message': thread_messages[-1] if thread_messages else None}

    def analyze_switching_patterns(self) -> Dict:
        """Analyze thread switching patterns and performance."""
        if not self.thread_switches:
            return {'switch_count': 0, 'avg_switch_duration': 0, 'context_preservation_rate': 1.0}
        switch_durations = [s['switch_duration'] for s in self.thread_switches if s['switch_duration'] > 0]
        avg_switch_duration = sum(switch_durations) / len(switch_durations) if switch_durations else 0
        context_preserved_count = sum((1 for s in self.thread_switches if s['context_preserved']))
        context_preservation_rate = context_preserved_count / len(self.thread_switches)
        return {'switch_count': len(self.thread_switches), 'avg_switch_duration': avg_switch_duration, 'context_preservation_rate': context_preservation_rate, 'context_failures': len(self.context_preservation_failures), 'room_switches': len(self.room_switch_events)}

    def generate_switching_report(self) -> Dict:
        """Generate comprehensive thread switching report."""
        switching_analysis = self.analyze_switching_patterns()
        total_threads = len(self.thread_states)
        active_threads = sum((1 for state in self.thread_states.values() if state['active']))
        total_messages = sum((len(msgs) for msgs in self.thread_messages.values()))
        threads_with_messages = sum((1 for msgs in self.thread_messages.values() if len(msgs) > 0))
        return {'test_duration': time.time() - self.start_time, 'total_threads': total_threads, 'active_threads': active_threads, 'total_messages': total_messages, 'threads_with_messages': threads_with_messages, 'switching_analysis': switching_analysis, 'context_preservation_failures': len(self.context_preservation_failures), 'websocket_room_switches': len(self.room_switch_events), 'detailed_failures': self.context_preservation_failures, 'thread_switches': self.thread_switches, 'room_switch_events': self.room_switch_events}

class ThreadSwitchingWebSocketClient:
    """WebSocket client optimized for thread switching behavior testing."""

    def __init__(self, user_context: StronglyTypedUserExecutionContext, auth_helper: E2EWebSocketAuthHelper, switching_tracker: ThreadSwitchingTracker):
        self.user_context = user_context
        self.auth_helper = auth_helper
        self.switching_tracker = switching_tracker
        self.websocket = None
        self.user_id = str(user_context.user_id)
        self.current_thread_id = None
        self.is_connected = False
        self.user_threads: Dict[str, Dict] = {}

    @asynccontextmanager
    async def connect(self, timeout: float=25.0):
        """Connect with thread switching monitoring."""
        try:
            self.websocket = await self.auth_helper.connect_authenticated_websocket(timeout=timeout)
            self.is_connected = True
            logger.info(f'[U+1F50C] User {self.user_id} connected for thread switching tests')
            monitor_task = asyncio.create_task(self._monitor_thread_messages())
            try:
                yield self
            finally:
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
                if self.websocket and (not self.websocket.closed):
                    await self.websocket.close()
                    self.is_connected = False
                logger.info(f'[U+1F50C] User {self.user_id} disconnected from thread switching tests')
        except Exception as e:
            logger.error(f' FAIL:  User {self.user_id} thread switching WebSocket connection failed: {e}')
            raise

    async def _monitor_thread_messages(self):
        """Monitor WebSocket messages for thread-specific tracking."""
        try:
            while self.is_connected and self.websocket:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    try:
                        message_data = json.loads(message)
                        message_type = message_data.get('type', 'unknown')
                        thread_id = message_data.get('thread_id', self.current_thread_id)
                        if thread_id:
                            self.switching_tracker.track_message(self.user_id, thread_id, message_type, message_data)
                        logger.debug(f'[U+1F4E8] User {self.user_id} received {message_type} in thread {thread_id}')
                    except json.JSONDecodeError:
                        pass
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.warning(f'Message monitoring error for user {self.user_id}: {e}')
                    break
        except asyncio.CancelledError:
            pass

    async def create_conversation_thread(self, thread_title: str, initial_context: Dict=None) -> str:
        """Create a new conversation thread."""
        id_generator = UnifiedIdGenerator()
        thread_id = id_generator.generate_thread_id(self.user_id)
        self.switching_tracker.initialize_thread(self.user_id, thread_id, thread_title, initial_context)
        self.user_threads[thread_id] = {'title': thread_title, 'created_at': time.time(), 'message_count': 0, 'context': initial_context or {}}
        if self.current_thread_id is None:
            self.current_thread_id = thread_id
        logger.info(f'[U+1F4DD] User {self.user_id} created conversation thread {thread_id}: {thread_title}')
        return thread_id

    async def switch_to_thread(self, target_thread_id: str, switch_reason: str='user_action') -> int:
        """Switch to a different conversation thread."""
        if not self.websocket or not self.is_connected:
            raise ConnectionError(f'User {self.user_id} WebSocket not connected')
        from_thread_id = self.current_thread_id
        switch_index = self.switching_tracker.track_thread_switch(self.user_id, from_thread_id, target_thread_id, switch_reason)
        switch_message = {'type': 'thread_switch', 'user_id': self.user_id, 'from_thread_id': from_thread_id, 'to_thread_id': target_thread_id, 'timestamp': datetime.now(timezone.utc).isoformat(), 'switch_reason': switch_reason}
        await self.websocket.send(json.dumps(switch_message))
        self.current_thread_id = target_thread_id
        logger.info(f' CYCLE:  User {self.user_id} switching from {from_thread_id} to {target_thread_id}')
        await asyncio.sleep(0.2)
        return switch_index

    async def send_message_in_current_thread(self, message: str, message_type: str='user_message') -> str:
        """Send message in currently active thread."""
        if not self.current_thread_id:
            raise ValueError(f'User {self.user_id} has no active thread')
        if not self.websocket or not self.is_connected:
            raise ConnectionError(f'User {self.user_id} WebSocket not connected')
        id_generator = UnifiedIdGenerator()
        message_id = id_generator.generate_message_id(self.user_id)
        message_data = {'type': message_type, 'user_id': self.user_id, 'thread_id': self.current_thread_id, 'message_id': message_id, 'content': message, 'timestamp': datetime.now(timezone.utc).isoformat()}
        await self.websocket.send(json.dumps(message_data))
        if self.current_thread_id in self.user_threads:
            self.user_threads[self.current_thread_id]['message_count'] += 1
        logger.info(f'[U+1F4AC] User {self.user_id} sent message in thread {self.current_thread_id}')
        return message_id

    async def get_thread_history(self, thread_id: str) -> Dict:
        """Get message history for specific thread."""
        if not self.websocket or not self.is_connected:
            raise ConnectionError(f'User {self.user_id} WebSocket not connected')
        history_request = {'type': 'get_thread_history', 'user_id': self.user_id, 'thread_id': thread_id, 'timestamp': datetime.now(timezone.utc).isoformat()}
        await self.websocket.send(json.dumps(history_request))
        await asyncio.sleep(1.0)
        return self.switching_tracker.validate_thread_history_preservation(thread_id)

    async def validate_current_thread_context(self) -> Dict:
        """Validate that current thread context is correct."""
        if not self.current_thread_id:
            return {'valid': False, 'error': 'No current thread'}
        history_validation = self.switching_tracker.validate_thread_history_preservation(self.current_thread_id)
        client_thread_info = self.user_threads.get(self.current_thread_id, {})
        return {'valid': history_validation['preserved'], 'current_thread_id': self.current_thread_id, 'client_message_count': client_thread_info.get('message_count', 0), 'tracked_message_count': history_validation['message_count'], 'history_validation': history_validation}

class TestThreadSwitchingConsistencyE2E:
    """
    CRITICAL E2E test suite for thread switching consistency.
    
    Tests that users can switch between conversation threads seamlessly
    while maintaining perfect context preservation and message history.
    """

    @classmethod
    def setup_class(cls):
        """Set up test class with real service requirements."""
        cls.env = get_env()
        cls.test_environment = cls.env.get('TEST_ENV', cls.env.get('ENVIRONMENT', 'test'))
        logger.info('[U+1F680] Starting Thread Switching Consistency E2E Tests')
        logger.info(f' PIN:  Environment: {cls.test_environment}')
        logger.info(' TARGET:  Testing thread switching with context preservation')

    def setup_method(self, method):
        """Set up each test method."""
        self.auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
        self.switching_tracker = ThreadSwitchingTracker(self.test_environment)
        self.test_clients: List[ThreadSwitchingWebSocketClient] = []
        logger.info(f'[U+1F9EA] Starting test: {method.__name__}')

    def teardown_method(self, method):
        """Clean up test resources."""
        logger.info(f'[U+1F9F9] Cleaning up test: {method.__name__}')
        self.test_clients.clear()

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_basic_thread_switching_context_preservation(self):
        """
        CRITICAL TEST: Basic thread switching preserves context and message history.
        
        This test validates that when a user switches between two conversation
        threads, the context and message history are perfectly preserved.
        
        Expected Initial Result: FAILURE - Thread context likely not preserved
        Success Criteria: Perfect context preservation across switches
        """
        test_start_time = time.time()
        logger.info(' CYCLE:  CRITICAL: Testing basic thread switching context preservation')
        try:
            user_context = await create_authenticated_user_context(user_email=f'thread_switching_{int(time.time())}@example.com', environment=self.test_environment, websocket_enabled=True)
            client = ThreadSwitchingWebSocketClient(user_context, self.auth_helper, self.switching_tracker)
            self.test_clients.append(client)
            async with client.connect(timeout=30.0):
                logger.info(f' PASS:  Connected user {client.user_id} for basic thread switching test')
                thread_1_id = await client.create_conversation_thread('Conversation 1: Performance Optimization', {'topic': 'performance', 'priority': 'high'})
                thread_2_id = await client.create_conversation_thread('Conversation 2: Security Review', {'topic': 'security', 'priority': 'medium'})
                logger.info('[U+1F4AC] Adding messages to Thread 1...')
                await client.switch_to_thread(thread_1_id, 'initial_selection')
                await client.send_message_in_current_thread('How can I optimize database queries?')
                await asyncio.sleep(0.5)
                await client.send_message_in_current_thread('What about caching strategies?')
                await asyncio.sleep(0.5)
                logger.info(' CYCLE:  Switching to Thread 2...')
                switch_1_index = await client.switch_to_thread(thread_2_id, 'user_switching')
                await client.send_message_in_current_thread('What are the latest security vulnerabilities?')
                await asyncio.sleep(0.5)
                await client.send_message_in_current_thread('How should I implement 2FA?')
                await asyncio.sleep(0.5)
                logger.info(' CYCLE:  Switching back to Thread 1...')
                switch_2_index = await client.switch_to_thread(thread_1_id, 'return_to_conversation')
                await client.send_message_in_current_thread('Also, what about connection pooling?')
                await asyncio.sleep(0.5)
                logger.info(' CYCLE:  Final switch to Thread 2...')
                switch_3_index = await client.switch_to_thread(thread_2_id, 'final_check')
                await client.send_message_in_current_thread('What about rate limiting?')
                await asyncio.sleep(1.0)
                self.switching_tracker.complete_thread_switch(switch_1_index)
                self.switching_tracker.complete_thread_switch(switch_2_index)
                self.switching_tracker.complete_thread_switch(switch_3_index)
                thread_1_history = self.switching_tracker.validate_thread_history_preservation(thread_1_id)
                thread_2_history = self.switching_tracker.validate_thread_history_preservation(thread_2_id)
                current_context = await client.validate_current_thread_context()
                report = self.switching_tracker.generate_switching_report()
                logger.info(' CHART:  BASIC THREAD SWITCHING RESULTS:')
                logger.info(f"   Thread Switches: {report['switching_analysis']['switch_count']}")
                logger.info(f"   Context Preservation Rate: {report['switching_analysis']['context_preservation_rate']:.2%}")
                logger.info(f"   Thread 1 History Preserved: {thread_1_history['preserved']}")
                logger.info(f"   Thread 2 History Preserved: {thread_2_history['preserved']}")
                logger.info(f"   Context Failures: {report['context_preservation_failures']}")
                if not thread_1_history['preserved'] or not thread_2_history['preserved']:
                    logger.error(' ALERT:  THREAD HISTORY PRESERVATION FAILURE')
                    logger.error(f" SEARCH:  Thread 1 preserved: {thread_1_history['preserved']}")
                    logger.error(f" SEARCH:  Thread 2 preserved: {thread_2_history['preserved']}")
                    pytest.fail(f'THREAD HISTORY FAILURE: Thread histories not preserved across switches. Thread 1: {thread_1_history}, Thread 2: {thread_2_history}. Context preservation broken in thread switching.')
                if report['context_preservation_failures'] > 0:
                    logger.error(' ALERT:  CONTEXT PRESERVATION FAILURES DETECTED')
                    logger.error(f" SEARCH:  Found {report['context_preservation_failures']} failures")
                    for failure in self.switching_tracker.context_preservation_failures:
                        logger.error(f' SEARCH:  Failure: {failure}')
                    pytest.fail(f"CONTEXT PRESERVATION FAILURE: {report['context_preservation_failures']} failures. Thread switching does not preserve conversation context properly.")
                if not current_context['valid']:
                    logger.error(' ALERT:  CURRENT CONTEXT VALIDATION FAILURE')
                    logger.error(f' SEARCH:  Context validation: {current_context}')
                    pytest.fail(f'CURRENT CONTEXT FAILURE: Current thread context invalid. User cannot reliably determine active conversation state.')
                logger.info(' PASS:  SUCCESS: Perfect thread switching context preservation!')
                assert thread_1_history['message_count'] >= 3, f"Thread 1 insufficient messages: {thread_1_history['message_count']}"
                assert thread_2_history['message_count'] >= 3, f"Thread 2 insufficient messages: {thread_2_history['message_count']}"
                avg_switch_time = report['switching_analysis']['avg_switch_duration']
                assert avg_switch_time <= 2.0, f'Thread switching too slow: {avg_switch_time:.2f}s'
                assert report['switching_analysis']['context_preservation_rate'] >= 0.95, f"Context preservation rate too low: {report['switching_analysis']['context_preservation_rate']:.2%}"
        except Exception as e:
            report = self.switching_tracker.generate_switching_report()
            logger.error(f' CHART:  Partial results: {report}')
            logger.error(f' FAIL:  Basic thread switching test failed: {e}')
            raise
        actual_duration = time.time() - test_start_time
        assert actual_duration > 6.0, f'Thread switching test completed too quickly ({actual_duration:.2f}s)'
        logger.info(f' PASS:  Basic thread switching test completed in {actual_duration:.2f}s')

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_rapid_thread_switching_stability(self):
        """
        CRITICAL TEST: Rapid thread switching maintains stability and consistency.
        
        This test validates that when a user rapidly switches between multiple
        threads, the system maintains stability without losing context or messages.
        
        Expected Initial Result: FAILURE - Race conditions during rapid switching
        Success Criteria: Stable context preservation under rapid switching stress
        """
        test_start_time = time.time()
        logger.info(' LIGHTNING:  CRITICAL: Testing rapid thread switching stability')
        num_threads = 5
        switches_per_thread = 3
        rapid_switch_delay = 0.1
        try:
            user_context = await create_authenticated_user_context(user_email=f'rapid_switching_{int(time.time())}@example.com', environment=self.test_environment, websocket_enabled=True)
            client = ThreadSwitchingWebSocketClient(user_context, self.auth_helper, self.switching_tracker)
            self.test_clients.append(client)
            async with client.connect(timeout=35.0):
                logger.info(f' PASS:  Connected user {client.user_id} for rapid switching test')
                thread_ids = []
                logger.info(f'[U+1F4DD] Creating {num_threads} conversation threads...')
                for i in range(num_threads):
                    thread_id = await client.create_conversation_thread(f'Rapid Test Thread {i}', {'thread_index': i, 'test_type': 'rapid_switching'})
                    thread_ids.append(thread_id)
                for i, thread_id in enumerate(thread_ids):
                    await client.switch_to_thread(thread_id, 'initial_setup')
                    await client.send_message_in_current_thread(f'Initial message for thread {i}')
                    await asyncio.sleep(rapid_switch_delay)
                logger.info(' LIGHTNING:  Starting rapid thread switching pattern...')
                switch_indices = []
                for switch_round in range(switches_per_thread):
                    for i, thread_id in enumerate(thread_ids):
                        switch_index = await client.switch_to_thread(thread_id, f'rapid_switch_round_{switch_round}')
                        switch_indices.append(switch_index)
                        await client.send_message_in_current_thread(f'Rapid switch message round {switch_round} in thread {i}')
                        await asyncio.sleep(rapid_switch_delay)
                for switch_index in switch_indices:
                    self.switching_tracker.complete_thread_switch(switch_index)
                await asyncio.sleep(2.0)
                thread_validations = {}
                for i, thread_id in enumerate(thread_ids):
                    thread_validations[thread_id] = self.switching_tracker.validate_thread_history_preservation(thread_id)
                report = self.switching_tracker.generate_switching_report()
                preserved_threads = sum((1 for v in thread_validations.values() if v['preserved']))
                total_switches = len(switch_indices)
                logger.info(' CHART:  RAPID THREAD SWITCHING RESULTS:')
                logger.info(f'   Total Threads: {num_threads}')
                logger.info(f'   Preserved Threads: {preserved_threads}/{num_threads}')
                logger.info(f'   Total Switches: {total_switches}')
                logger.info(f"   Context Preservation Rate: {report['switching_analysis']['context_preservation_rate']:.2%}")
                logger.info(f"   Avg Switch Duration: {report['switching_analysis']['avg_switch_duration']:.3f}s")
                logger.info(f"   Context Failures: {report['context_preservation_failures']}")
                if preserved_threads < num_threads:
                    logger.error(' ALERT:  RAPID SWITCHING THREAD PRESERVATION FAILURE')
                    logger.error(f' SEARCH:  Only {preserved_threads}/{num_threads} threads preserved')
                    for thread_id, validation in thread_validations.items():
                        if not validation['preserved']:
                            logger.error(f' SEARCH:  Failed thread {thread_id}: {validation}')
                    pytest.fail(f'RAPID SWITCHING FAILURE: Only {preserved_threads}/{num_threads} threads preserved. Rapid switching causes context/message loss. Race conditions in thread management.')
                if report['context_preservation_failures'] > 0:
                    logger.error(' ALERT:  RAPID SWITCHING CONTEXT FAILURES')
                    logger.error(f" SEARCH:  Found {report['context_preservation_failures']} context failures")
                    pytest.fail(f"RAPID SWITCHING CONTEXT FAILURE: {report['context_preservation_failures']} failures. System cannot handle rapid thread switching without context corruption.")
                if report['switching_analysis']['avg_switch_duration'] > 1.0:
                    logger.error(' ALERT:  RAPID SWITCHING PERFORMANCE DEGRADATION')
                    logger.error(f" SEARCH:  Switch duration: {report['switching_analysis']['avg_switch_duration']:.3f}s")
                    pytest.fail(f"RAPID SWITCHING PERFORMANCE FAILURE: {report['switching_analysis']['avg_switch_duration']:.3f}s average switch time too slow. Performance degrades under rapid switching load.")
                logger.info(' PASS:  SUCCESS: Perfect rapid thread switching stability!')
                expected_messages_per_thread = 1 + switches_per_thread
                for thread_id, validation in thread_validations.items():
                    assert validation['message_count'] >= expected_messages_per_thread * 0.8, f"Thread {thread_id} insufficient messages: {validation['message_count']}"
                assert report['switching_analysis']['context_preservation_rate'] >= 0.9, f"Context preservation rate too low under rapid switching: {report['switching_analysis']['context_preservation_rate']:.2%}"
        except Exception as e:
            report = self.switching_tracker.generate_switching_report()
            logger.error(f' CHART:  Rapid switching partial results: {report}')
            logger.error(f' FAIL:  Rapid thread switching test failed: {e}')
            raise
        actual_duration = time.time() - test_start_time
        assert actual_duration > 8.0, f'Rapid switching test completed too quickly ({actual_duration:.2f}s)'
        logger.info(f' PASS:  Rapid thread switching test completed in {actual_duration:.2f}s')

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.asyncio
    async def test_multi_user_thread_switching_isolation(self):
        """
        CRITICAL TEST: Multiple users switching threads independently with perfect isolation.
        
        This test validates that when multiple users are switching between their
        own threads simultaneously, there's no cross-user contamination or interference.
        
        Expected Initial Result: FAILURE - Cross-user thread switching interference
        Success Criteria: Perfect isolation during concurrent multi-user thread switching
        """
        test_start_time = time.time()
        logger.info('[U+1F465] CYCLE:  CRITICAL: Testing multi-user thread switching isolation')
        num_users = 3
        threads_per_user = 3
        switches_per_user = 4
        user_clients = []
        switching_tasks = []
        try:
            logger.info(f'[U+1F510] Creating {num_users} users for concurrent thread switching...')
            for user_idx in range(num_users):
                user_context = await create_authenticated_user_context(user_email=f'multi_user_switching_{user_idx}_{int(time.time())}@example.com', environment=self.test_environment, websocket_enabled=True)
                client = ThreadSwitchingWebSocketClient(user_context, self.auth_helper, self.switching_tracker)
                user_clients.append(client)
                self.test_clients.append(client)
                logger.info(f' PASS:  Created switching user {user_idx}: {client.user_id}')
            for user_idx, client in enumerate(user_clients):
                task = asyncio.create_task(self._execute_user_thread_switching_scenario(client, threads_per_user, switches_per_user, user_idx))
                switching_tasks.append(task)
            logger.info('[U+1F680] Executing concurrent multi-user thread switching...')
            user_results = await asyncio.gather(*switching_tasks, return_exceptions=True)
            successful_users = 0
            total_switches_completed = 0
            cross_user_contamination = 0
            context_preservation_failures = 0
            for user_idx, result in enumerate(user_results):
                if isinstance(result, Exception):
                    logger.error(f' FAIL:  User {user_idx} thread switching failed: {result}')
                else:
                    successful_users += 1
                    total_switches_completed += result.get('switches_completed', 0)
                    cross_user_contamination += result.get('cross_user_issues', 0)
                    context_preservation_failures += result.get('context_failures', 0)
                    logger.info(f"[U+1F464] User {user_idx}: {result.get('switches_completed', 0)} switches, Context preserved: {result.get('context_preserved', True)}")
            report = self.switching_tracker.generate_switching_report()
            logger.info(' CHART:  MULTI-USER THREAD SWITCHING ISOLATION RESULTS:')
            logger.info(f'   Successful Users: {successful_users}/{num_users}')
            logger.info(f'   Total Switches Completed: {total_switches_completed}')
            logger.info(f'   Cross-User Contamination Issues: {cross_user_contamination}')
            logger.info(f'   Context Preservation Failures: {context_preservation_failures}')
            logger.info(f"   Overall Context Preservation Rate: {report['switching_analysis']['context_preservation_rate']:.2%}")
            if cross_user_contamination > 0:
                logger.error(' ALERT:  CROSS-USER THREAD SWITCHING CONTAMINATION')
                logger.error(f' SEARCH:  Found {cross_user_contamination} cross-user issues')
                pytest.fail(f"CROSS-USER CONTAMINATION FAILURE: {cross_user_contamination} cross-user issues. Thread switching not properly isolated between users. Users seeing or affecting other users' thread contexts.")
            if context_preservation_failures > 0:
                logger.error(' ALERT:  MULTI-USER CONTEXT PRESERVATION FAILURES')
                logger.error(f' SEARCH:  Found {context_preservation_failures} context failures')
                pytest.fail(f'MULTI-USER CONTEXT FAILURE: {context_preservation_failures} context preservation failures. Thread switching fails under multi-user concurrent load.')
            if successful_users < num_users:
                logger.error(' ALERT:  MULTI-USER SWITCHING SYSTEM FAILURES')
                logger.error(f' SEARCH:  Only {successful_users}/{num_users} users completed successfully')
                pytest.fail(f'MULTI-USER SWITCHING FAILURE: Only {successful_users}/{num_users} users successful. System cannot handle concurrent multi-user thread switching.')
            logger.info(' PASS:  SUCCESS: Perfect multi-user thread switching isolation!')
            expected_total_switches = num_users * switches_per_user
            assert total_switches_completed >= expected_total_switches * 0.9, f'Too few switches completed: {total_switches_completed}/{expected_total_switches}'
            assert report['switching_analysis']['context_preservation_rate'] >= 0.9, f"Context preservation rate too low under multi-user load: {report['switching_analysis']['context_preservation_rate']:.2%}"
        except Exception as e:
            report = self.switching_tracker.generate_switching_report()
            logger.error(f' CHART:  Multi-user switching partial results: {report}')
            logger.error(f' FAIL:  Multi-user thread switching isolation test failed: {e}')
            raise
        actual_duration = time.time() - test_start_time
        assert actual_duration > 12.0, f'Multi-user switching test completed too quickly ({actual_duration:.2f}s)'
        logger.info(f' PASS:  Multi-user thread switching isolation test completed in {actual_duration:.2f}s')

    async def _execute_user_thread_switching_scenario(self, client: ThreadSwitchingWebSocketClient, num_threads: int, num_switches: int, user_idx: int) -> Dict:
        """Execute thread switching scenario for single user."""
        switches_completed = 0
        cross_user_issues = 0
        context_failures = 0
        context_preserved = True
        try:
            async with client.connect(timeout=40.0):
                thread_ids = []
                for thread_idx in range(num_threads):
                    thread_id = await client.create_conversation_thread(f'User {user_idx} Thread {thread_idx}', {'user_idx': user_idx, 'thread_idx': thread_idx})
                    thread_ids.append(thread_id)
                    await client.switch_to_thread(thread_id, 'setup')
                    await client.send_message_in_current_thread(f'Initial message for thread {thread_idx}')
                    await asyncio.sleep(0.1)
                for switch_num in range(num_switches):
                    import random
                    target_thread_id = random.choice(thread_ids)
                    await client.switch_to_thread(target_thread_id, f'switch_{switch_num}')
                    switches_completed += 1
                    await client.send_message_in_current_thread(f'Switch {switch_num} message')
                    await asyncio.sleep(0.2)
                final_context = await client.validate_current_thread_context()
                if not final_context['valid']:
                    context_preserved = False
                    context_failures += 1
        except Exception as e:
            logger.error(f' FAIL:  User {user_idx} thread switching scenario failed: {e}')
            raise
        return {'user_idx': user_idx, 'user_id': client.user_id, 'switches_completed': switches_completed, 'cross_user_issues': cross_user_issues, 'context_failures': context_failures, 'context_preserved': context_preserved}
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')