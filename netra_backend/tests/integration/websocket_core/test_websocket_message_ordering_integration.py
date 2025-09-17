"""
WebSocket Message Ordering Integration Tests

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Chat Conversation Coherence
- Value Impact: Ensures message chronology is preserved during concurrent operations
- Strategic Impact: Critical for chat UX - prevents confusing out-of-order message delivery

This test suite validates WebSocket message ordering guarantees during:
- Concurrent message operations from multiple sources
- High-frequency message streams
- Mixed message types and priorities
- Race conditions and timing-sensitive scenarios
- Message batching and queuing operations

BUSINESS IMPACT: Maintains logical conversation flow that users expect in chat applications.
"""
import asyncio
import pytest
import uuid
import time
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from unittest.mock import AsyncMock, Mock, MagicMock
from collections import defaultdict, deque
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager, WebSocketConnection
from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory, UserWebSocketEmitter, WebSocketEvent
from test_framework.ssot.base_test_case import SSotBaseTestCase
logger = central_logger.get_logger(__name__)

class OrderedWebSocketMock:
    """Mock WebSocket that preserves message ordering for testing."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._messages = []
        self._message_timestamps = []
        self._send_delays = {}
        self._send_lock = asyncio.Lock()
        self.send_json = AsyncMock(side_effect=self._send_json_impl)

    async def _send_json_impl(self, data):
        """Send JSON with ordering preservation."""
        async with self._send_lock:
            message_id = data.get('message_id') or data.get('event_id') or str(uuid.uuid4())
            delay = self._send_delays.get(message_id, 0.0)
            if delay > 0:
                await asyncio.sleep(delay)
            timestamp = time.time_ns()
            self._messages.append({'data': data.copy() if isinstance(data, dict) else data, 'timestamp_ns': timestamp, 'timestamp_dt': datetime.now(timezone.utc), 'user_id': self.user_id, 'message_id': message_id, 'send_order': len(self._messages)})
            self._message_timestamps.append(timestamp)

    def set_message_delay(self, message_id: str, delay: float):
        """Set artificial delay for specific message."""
        self._send_delays[message_id] = delay

    def clear_messages(self):
        """Clear all recorded messages."""
        self._messages.clear()
        self._message_timestamps.clear()

    def get_messages(self) -> List[Dict]:
        """Get all messages in send order."""
        return self._messages.copy()

    def get_message_sequence_numbers(self) -> List[int]:
        """Extract sequence numbers from messages."""
        sequences = []
        for msg in self._messages:
            data = msg['data']
            seq = data.get('sequence') or data.get('sequence_number') or data.get('message_index') or data.get('order')
            if seq is not None:
                sequences.append(seq)
        return sequences

    def verify_timestamp_ordering(self) -> bool:
        """Verify messages are ordered by timestamp."""
        timestamps = self._message_timestamps
        return timestamps == sorted(timestamps)

@pytest.mark.integration
class WebSocketMessageOrderingIntegrationTests(SSotBaseTestCase):
    """
    Integration tests for WebSocket message ordering guarantees.
    
    Tests critical ordering scenarios that affect chat business value:
    - Sequential message delivery preservation
    - Concurrent operation ordering guarantees
    - Message priority and batching behavior
    - Race condition handling
    - High-frequency message stream ordering
    
    BUSINESS IMPACT: Ensures chat conversations remain coherent and logical.
    """

    async def asyncSetUp(self):
        """Set up WebSocket message ordering test environment."""
        await super().asyncSetUp()
        self.ws_manager = UnifiedWebSocketManager()
        self.test_users = {}
        self.ordered_websockets = {}
        user_count = 6
        for i in range(user_count):
            user_id = f'ordering_user_{i:02d}'
            connection_id = str(uuid.uuid4())
            ordered_ws = OrderedWebSocketMock(user_id)
            connection = WebSocketConnection(connection_id=connection_id, user_id=user_id, websocket=ordered_ws, connected_at=datetime.now(timezone.utc))
            await self.ws_manager.add_connection(connection)
            self.test_users[user_id] = {'connection_id': connection_id, 'thread_id': f'thread_{i:02d}'}
            self.ordered_websockets[user_id] = ordered_ws
        logger.info(f'Message ordering test setup completed with {user_count} users')

    async def test_sequential_message_ordering(self):
        """
        Test that sequentially sent messages maintain their order.
        
        BVJ: Foundation of chat coherence - messages sent in sequence
        must be delivered in the same sequence to maintain conversation logic.
        """
        user_id = 'ordering_user_00'
        ordered_ws = self.ordered_websockets[user_id]
        ordered_ws.clear_messages()
        message_count = 50
        sent_messages = []
        for i in range(message_count):
            message = {'type': 'sequential_test', 'sequence': i, 'content': f'Sequential message {i}', 'timestamp': datetime.now(timezone.utc).isoformat(), 'message_id': f'seq_{i:03d}'}
            sent_messages.append(message)
            await self.ws_manager.send_to_user(user_id, message)
            await asyncio.sleep(0.001)
        await asyncio.sleep(0.5)
        received_messages = ordered_ws.get_messages()
        self.assertEqual(len(received_messages), message_count, f'Should receive all {message_count} messages')
        sequences = ordered_ws.get_message_sequence_numbers()
        expected_sequences = list(range(message_count))
        self.assertEqual(sequences, expected_sequences, 'Message sequence numbers should be in order')
        self.assertTrue(ordered_ws.verify_timestamp_ordering(), 'Messages should be ordered by send timestamp')
        for i, received_msg in enumerate(received_messages):
            data = received_msg['data']
            expected_content = f'Sequential message {i}'
            self.assertEqual(data['content'], expected_content, f'Message {i} content should match expected')

    async def test_concurrent_message_ordering(self):
        """
        Test message ordering with concurrent senders.
        
        BVJ: Critical for multi-component chat systems where agents, tools,
        and system notifications may send messages concurrently.
        """
        user_id = 'ordering_user_01'
        ordered_ws = self.ordered_websockets[user_id]
        ordered_ws.clear_messages()

        async def send_message_batch(batch_id: str, start_seq: int, count: int):
            """Send batch of messages from specific source."""
            batch_messages = []
            for i in range(count):
                seq = start_seq + i
                message = {'type': 'concurrent_test', 'batch_id': batch_id, 'sequence': seq, 'content': f'Batch {batch_id} message {i}', 'global_sequence': seq, 'timestamp': datetime.now(timezone.utc).isoformat()}
                batch_messages.append(message)
                await self.ws_manager.send_to_user(user_id, message)
                await asyncio.sleep(0.0001)
            return batch_messages
        batch_size = 20
        batches = [('agent', 0, batch_size), ('tool', batch_size, batch_size), ('system', batch_size * 2, batch_size)]
        tasks = [send_message_batch(batch_id, start, count) for batch_id, start, count in batches]
        sent_batches = await asyncio.gather(*tasks)
        await asyncio.sleep(1.0)
        received_messages = ordered_ws.get_messages()
        total_expected = sum((count for _, _, count in batches))
        self.assertEqual(len(received_messages), total_expected, f'Should receive all {total_expected} concurrent messages')
        batch_sequences = defaultdict(list)
        for msg in received_messages:
            data = msg['data']
            batch_id = data.get('batch_id')
            sequence = data.get('sequence')
            if batch_id and sequence is not None:
                batch_sequences[batch_id].append(sequence)
        for batch_id, sequences in batch_sequences.items():
            expected_start = {'agent': 0, 'tool': 20, 'system': 40}[batch_id]
            expected_sequences = list(range(expected_start, expected_start + batch_size))
            self.assertEqual(sorted(sequences), expected_sequences, f'Batch {batch_id} should have correct sequences')
        self.assertTrue(ordered_ws.verify_timestamp_ordering(), 'Overall timestamp ordering should be maintained')

    async def test_mixed_priority_message_ordering(self):
        """
        Test ordering with mixed message types and priorities.
        
        BVJ: Chat systems have different message types (agent responses, tool outputs,
        system notifications) that should maintain logical ordering.
        """
        user_id = 'ordering_user_02'
        ordered_ws = self.ordered_websockets[user_id]
        ordered_ws.clear_messages()
        message_types = [{'type': 'agent_thinking', 'priority': 'normal', 'frequency': 'high'}, {'type': 'tool_executing', 'priority': 'high', 'frequency': 'medium'}, {'type': 'agent_result', 'priority': 'critical', 'frequency': 'low'}, {'type': 'system_notification', 'priority': 'low', 'frequency': 'rare'}]
        sent_messages = []
        message_sequence = 0
        for cycle in range(10):
            for msg_type in message_types:
                count = {'high': 5, 'medium': 3, 'low': 2, 'rare': 1}[msg_type['frequency']]
                for i in range(count):
                    message = {'type': msg_type['type'], 'priority': msg_type['priority'], 'cycle': cycle, 'sequence': message_sequence, 'content': f"Cycle {cycle}, {msg_type['type']} #{i}", 'timestamp': datetime.now(timezone.utc).isoformat()}
                    sent_messages.append(message)
                    await self.ws_manager.send_to_user(user_id, message)
                    message_sequence += 1
                    delay = {'high': 0.001, 'medium': 0.002, 'low': 0.005, 'rare': 0.01}[msg_type['frequency']]
                    await asyncio.sleep(delay)
        await asyncio.sleep(1.0)
        received_messages = ordered_ws.get_messages()
        self.assertEqual(len(received_messages), len(sent_messages), 'Should receive all mixed-type messages')
        received_sequences = [msg['data'].get('sequence') for msg in received_messages]
        expected_sequences = list(range(len(sent_messages)))
        self.assertEqual(received_sequences, expected_sequences, 'Mixed message types should maintain sequence order')
        type_sequences = defaultdict(list)
        for msg in received_messages:
            data = msg['data']
            msg_type = data.get('type')
            cycle = data.get('cycle')
            if msg_type and cycle is not None:
                type_sequences[msg_type].append(cycle)
        for msg_type, cycles in type_sequences.items():
            for i in range(1, len(cycles)):
                self.assertGreaterEqual(cycles[i], cycles[i - 1], f'{msg_type} cycles should be non-decreasing')

    async def test_high_frequency_message_stream_ordering(self):
        """
        Test ordering under high-frequency message streams.
        
        BVJ: Critical for real-time chat features like typing indicators,
        live agent reasoning, or streaming responses.
        """
        user_id = 'ordering_user_03'
        ordered_ws = self.ordered_websockets[user_id]
        ordered_ws.clear_messages()
        message_count = 200
        messages_per_second = 100
        delay_between = 1.0 / messages_per_second
        start_time = time.time()
        for i in range(message_count):
            message = {'type': 'high_frequency_stream', 'sequence': i, 'content': f'Stream message {i}', 'timestamp': datetime.now(timezone.utc).isoformat(), 'stream_time': time.time() - start_time}
            await self.ws_manager.send_to_user(user_id, message)
            await asyncio.sleep(delay_between)
        await asyncio.sleep(2.0)
        end_time = time.time()
        total_time = end_time - start_time
        logger.info(f'High frequency test: {message_count} messages in {total_time:.2f}s ({message_count / total_time:.1f} msg/s)')
        received_messages = ordered_ws.get_messages()
        delivery_rate = len(received_messages) / message_count
        self.assertGreater(delivery_rate, 0.9, f'Should deliver >90% of high-frequency messages: {delivery_rate:.1%}')
        sequences = ordered_ws.get_message_sequence_numbers()
        for i in range(1, len(sequences)):
            self.assertGreater(sequences[i], sequences[i - 1], f'High frequency sequences should be strictly increasing: pos {i}: {sequences[i]} should be > {sequences[i - 1]}')
        self.assertTrue(ordered_ws.verify_timestamp_ordering(), 'High frequency messages should maintain timestamp order')

    async def test_race_condition_ordering(self):
        """
        Test ordering under race condition scenarios.
        
        BVJ: Prevents message scrambling during peak chat usage when
        multiple system components send messages simultaneously.
        """
        user_id = 'ordering_user_04'
        ordered_ws = self.ordered_websockets[user_id]
        ordered_ws.clear_messages()

        async def send_with_controlled_timing(message_id: str, sequence: int, delay: float):
            """Send message with controlled timing to create races."""
            ordered_ws.set_message_delay(message_id, delay)
            message = {'type': 'race_condition_test', 'message_id': message_id, 'sequence': sequence, 'content': f'Race message {sequence}', 'artificial_delay': delay, 'timestamp': datetime.now(timezone.utc).isoformat()}
            await self.ws_manager.send_to_user(user_id, message)
        race_tasks = []
        for i in range(20):
            message_id = f'race_{i:03d}'
            delay = random.uniform(0.0, 0.1)
            task = send_with_controlled_timing(message_id, i, delay)
            race_tasks.append(task)
        await asyncio.gather(*race_tasks)
        await asyncio.sleep(2.0)
        received_messages = ordered_ws.get_messages()
        self.assertEqual(len(received_messages), 20, 'Should receive all race condition messages')
        delivery_order = []
        original_sequences = []
        for msg in received_messages:
            data = msg['data']
            sequence = data.get('sequence')
            if sequence is not None:
                delivery_order.append(len(delivery_order))
                original_sequences.append(sequence)
        self.assertEqual(len(set(original_sequences)), 20, 'All original sequences should be unique')
        self.assertEqual(sorted(original_sequences), list(range(20)), 'All original sequences should be present')

    async def test_message_batching_ordering(self):
        """
        Test ordering when messages are batched or queued.
        
        BVJ: Ensures batching optimizations don't break message chronology.
        Critical for performance optimizations that must preserve UX.
        """
        user_id = 'ordering_user_05'
        ordered_ws = self.ordered_websockets[user_id]
        ordered_ws.clear_messages()
        batch_sizes = [5, 10, 8, 12, 6]
        total_messages = 0
        for batch_num, batch_size in enumerate(batch_sizes):
            logger.info(f'Sending batch {batch_num} with {batch_size} messages')
            for i in range(batch_size):
                message = {'type': 'batching_test', 'batch_number': batch_num, 'within_batch_sequence': i, 'global_sequence': total_messages, 'content': f'Batch {batch_num}, Message {i}', 'timestamp': datetime.now(timezone.utc).isoformat()}
                await self.ws_manager.send_to_user(user_id, message)
                total_messages += 1
                await asyncio.sleep(0.0001)
            await asyncio.sleep(0.1)
        await asyncio.sleep(1.0)
        received_messages = ordered_ws.get_messages()
        self.assertEqual(len(received_messages), total_messages, f'Should receive all {total_messages} batched messages')
        global_sequences = [msg['data'].get('global_sequence') for msg in received_messages]
        expected_global = list(range(total_messages))
        self.assertEqual(global_sequences, expected_global, 'Global sequence should be maintained across batches')
        batch_numbers = [msg['data'].get('batch_number') for msg in received_messages]
        for i in range(1, len(batch_numbers)):
            self.assertGreaterEqual(batch_numbers[i], batch_numbers[i - 1], f'Batch numbers should be non-decreasing: {batch_numbers[i]} should be >= {batch_numbers[i - 1]}')
        current_batch = -1
        within_batch_seq = -1
        for msg in received_messages:
            data = msg['data']
            batch_num = data.get('batch_number')
            batch_seq = data.get('within_batch_sequence')
            if batch_num != current_batch:
                current_batch = batch_num
                within_batch_seq = -1
            if batch_seq is not None:
                self.assertGreater(batch_seq, within_batch_seq, f'Within-batch sequence should increase: batch {batch_num}, seq {batch_seq} should be > {within_batch_seq}')
                within_batch_seq = batch_seq

    async def test_multi_user_ordering_isolation(self):
        """
        Test that message ordering is maintained independently per user.
        
        BVJ: Critical for multi-user chat - User A's message ordering
        should not be affected by User B's message patterns.
        """
        test_user_ids = list(self.test_users.keys())[:4]
        for user_id in test_user_ids:
            self.ordered_websockets[user_id].clear_messages()

        async def send_user_pattern(user_id: str, pattern: str):
            """Send specific message pattern to user."""
            if pattern == 'sequential':
                for i in range(30):
                    message = {'type': 'isolation_test', 'pattern': pattern, 'sequence': i, 'content': f'Sequential {i} for {user_id}', 'user_id': user_id}
                    await self.ws_manager.send_to_user(user_id, message)
                    await asyncio.sleep(0.01)
            elif pattern == 'burst':
                for i in range(15):
                    message = {'type': 'isolation_test', 'pattern': pattern, 'sequence': i, 'content': f'Burst {i} for {user_id}', 'user_id': user_id}
                    await self.ws_manager.send_to_user(user_id, message)
            elif pattern == 'sparse':
                for i in range(10):
                    message = {'type': 'isolation_test', 'pattern': pattern, 'sequence': i, 'content': f'Sparse {i} for {user_id}', 'user_id': user_id}
                    await self.ws_manager.send_to_user(user_id, message)
                    await asyncio.sleep(0.05)
            elif pattern == 'random':
                for i in range(20):
                    message = {'type': 'isolation_test', 'pattern': pattern, 'sequence': i, 'content': f'Random {i} for {user_id}', 'user_id': user_id}
                    await self.ws_manager.send_to_user(user_id, message)
                    await asyncio.sleep(random.uniform(0.001, 0.02))
        patterns = ['sequential', 'burst', 'sparse', 'random']
        user_patterns = {user_id: patterns[i] for i, user_id in enumerate(test_user_ids)}
        tasks = [send_user_pattern(user_id, pattern) for user_id, pattern in user_patterns.items()]
        await asyncio.gather(*tasks)
        await asyncio.sleep(2.0)
        for user_id, pattern in user_patterns.items():
            ordered_ws = self.ordered_websockets[user_id]
            received_messages = ordered_ws.get_messages()
            for msg in received_messages:
                data = msg['data']
                self.assertEqual(data.get('user_id'), user_id, f'Message should belong to {user_id}')
                self.assertEqual(data.get('pattern'), pattern, f'Message should have pattern {pattern}')
            sequences = [msg['data'].get('sequence') for msg in received_messages]
            expected_count = {'sequential': 30, 'burst': 15, 'sparse': 10, 'random': 20}[pattern]
            self.assertEqual(len(sequences), expected_count, f'User {user_id} ({pattern}) should receive {expected_count} messages')
            expected_sequences = list(range(expected_count))
            self.assertEqual(sequences, expected_sequences, f'User {user_id} ({pattern}) should have ordered sequences')
            self.assertTrue(ordered_ws.verify_timestamp_ordering(), f'User {user_id} ({pattern}) should have timestamp ordering')

    async def asyncTearDown(self):
        """Clean up message ordering test resources."""
        for user_id, user_data in self.test_users.items():
            connection_id = user_data['connection_id']
            await self.ws_manager.remove_connection(connection_id)
        self.test_users.clear()
        self.ordered_websockets.clear()
        await super().asyncTearDown()
        logger.info('Message ordering test teardown completed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')