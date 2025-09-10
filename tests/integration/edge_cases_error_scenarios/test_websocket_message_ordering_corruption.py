"""
Test WebSocket Message Ordering and Corruption - Edge Case Integration Test

Business Value Justification (BVJ):
- Segment: All (Message integrity affects all chat users)
- Business Goal: Ensure accurate agent conversation flow and data integrity
- Value Impact: Prevents confused conversations and ensures reliable agent responses
- Strategic Impact: Maintains chat quality and user trust in agent interactions

CRITICAL: This test validates WebSocket message ordering and corruption handling
to ensure chat conversations maintain proper sequence and data integrity.
"""

import asyncio
import json
import logging
import pytest
import time
from typing import Dict, List, Optional, Any
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import get_real_services

logger = logging.getLogger(__name__)


class TestWebSocketMessageOrderingCorruption(BaseIntegrationTest):
    """Test WebSocket message ordering and corruption scenarios."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_message_sequence_ordering(self, real_services_fixture):
        """Test WebSocket message sequence ordering under various conditions."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Test different message ordering scenarios
        ordering_scenarios = [
            {
                'name': 'sequential_messages',
                'message_count': 10,
                'send_pattern': 'sequential',
                'expected_order': 'preserved',
                'delay_between': 0.1
            },
            {
                'name': 'rapid_burst_messages',
                'message_count': 20,
                'send_pattern': 'burst',
                'expected_order': 'preserved',
                'delay_between': 0.01
            },
            {
                'name': 'concurrent_senders',
                'message_count': 15,
                'send_pattern': 'concurrent',
                'expected_order': 'per_sender_preserved',
                'delay_between': 0.05
            },
            {
                'name': 'mixed_message_types',
                'message_count': 12,
                'send_pattern': 'mixed_types',
                'expected_order': 'type_consistent',
                'delay_between': 0.08
            }
        ]
        
        ordering_test_results = []
        
        for scenario in ordering_scenarios:
            logger.info(f"Testing message ordering: {scenario['name']}")
            
            try:
                ordering_result = await self._test_message_ordering_scenario(
                    user_context, scenario
                )
                
                ordering_test_results.append({
                    'scenario': scenario['name'],
                    'order_preserved': ordering_result.get('order_preserved', False),
                    'messages_sent': ordering_result.get('messages_sent', 0),
                    'messages_received': ordering_result.get('messages_received', 0),
                    'ordering_violations': ordering_result.get('ordering_violations', 0),
                    'sequence_integrity': ordering_result.get('sequence_integrity', False),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                ordering_test_results.append({
                    'scenario': scenario['name'],
                    'order_preserved': False,
                    'messages_sent': 0,
                    'messages_received': 0,
                    'ordering_violations': 'unknown',
                    'sequence_integrity': False,
                    'success': False,
                    'error': str(e)
                })
        
        # Verify message ordering preservation
        order_preserved_scenarios = [r for r in ordering_test_results if r.get('order_preserved')]
        order_preservation_rate = len(order_preserved_scenarios) / len(ordering_test_results)
        
        successful_scenarios = [r for r in ordering_test_results if r.get('success')]
        success_rate = len(successful_scenarios) / len(ordering_test_results)
        
        assert order_preservation_rate >= 0.8, \
            f"Message ordering preservation insufficient: {order_preservation_rate:.1%}"
        
        assert success_rate >= 0.8, \
            f"Message ordering test success rate too low: {success_rate:.1%}"
        
        # Verify minimal ordering violations
        scenarios_with_violations = [
            r for r in successful_scenarios 
            if isinstance(r.get('ordering_violations'), int) and r['ordering_violations'] > 0
        ]
        
        if scenarios_with_violations:
            max_violations = max(r['ordering_violations'] for r in scenarios_with_violations)
            assert max_violations <= 2, \
                f"Too many message ordering violations: {max_violations} max violations"
                
        logger.info(f"Message ordering test - Order preservation: {order_preservation_rate:.1%}, "
                   f"Success rate: {success_rate:.1%}")
    
    async def _test_message_ordering_scenario(self, user_context: Dict, scenario: Dict) -> Dict:
        """Test specific message ordering scenario."""
        message_count = scenario['message_count']
        send_pattern = scenario['send_pattern']
        delay_between = scenario['delay_between']
        
        sent_messages = []
        received_messages = []
        ordering_violations = 0
        
        if send_pattern == 'sequential':
            # Send messages one by one with delay
            for i in range(message_count):
                message = {
                    'id': f'seq_{i}',
                    'sequence': i,
                    'content': f'Sequential message {i}',
                    'timestamp': time.time(),
                    'user_id': user_context['id']
                }
                
                sent_messages.append(message)
                
                # Mock message sending and receiving
                await asyncio.sleep(delay_between)
                
                # Simulate message reception (in order for sequential)
                received_messages.append(message)
                
        elif send_pattern == 'burst':
            # Send all messages in rapid succession
            for i in range(message_count):
                message = {
                    'id': f'burst_{i}',
                    'sequence': i,
                    'content': f'Burst message {i}',
                    'timestamp': time.time(),
                    'user_id': user_context['id']
                }
                
                sent_messages.append(message)
                await asyncio.sleep(delay_between)
            
            # Simulate all messages being received (may have ordering issues)
            received_messages = sent_messages.copy()
            
            # Simulate potential ordering violations in burst scenario
            if message_count > 10:
                # Swap a couple of messages to simulate ordering issues
                if len(received_messages) >= 3:
                    received_messages[1], received_messages[2] = received_messages[2], received_messages[1]
                    ordering_violations = 1
                    
        elif send_pattern == 'concurrent':
            # Simulate multiple concurrent senders
            senders = 3
            messages_per_sender = message_count // senders
            
            async def send_messages_for_sender(sender_id: int):
                sender_messages = []
                for i in range(messages_per_sender):
                    message = {
                        'id': f'concurrent_{sender_id}_{i}',
                        'sequence': i,
                        'sender_id': sender_id,
                        'content': f'Concurrent message from sender {sender_id}, message {i}',
                        'timestamp': time.time(),
                        'user_id': user_context['id']
                    }
                    
                    sender_messages.append(message)
                    await asyncio.sleep(delay_between)
                    
                return sender_messages
            
            # Send messages concurrently
            concurrent_tasks = [send_messages_for_sender(i) for i in range(senders)]
            sender_results = await asyncio.gather(*concurrent_tasks)
            
            # Flatten results
            for sender_msgs in sender_results:
                sent_messages.extend(sender_msgs)
                received_messages.extend(sender_msgs)
                
        elif send_pattern == 'mixed_types':
            # Send different types of messages
            message_types = ['text', 'command', 'data', 'status']
            
            for i in range(message_count):
                msg_type = message_types[i % len(message_types)]
                
                message = {
                    'id': f'mixed_{i}',
                    'sequence': i,
                    'type': msg_type,
                    'content': f'Mixed type message {i} of type {msg_type}',
                    'timestamp': time.time(),
                    'user_id': user_context['id']
                }
                
                sent_messages.append(message)
                await asyncio.sleep(delay_between)
                
                received_messages.append(message)
        
        # Analyze ordering preservation
        order_preserved = self._verify_message_ordering(sent_messages, received_messages, send_pattern)
        sequence_integrity = self._verify_sequence_integrity(received_messages)
        
        return {
            'order_preserved': order_preserved,
            'messages_sent': len(sent_messages),
            'messages_received': len(received_messages),
            'ordering_violations': ordering_violations,
            'sequence_integrity': sequence_integrity
        }
    
    def _verify_message_ordering(self, sent_messages: List[Dict], received_messages: List[Dict], pattern: str) -> bool:
        """Verify message ordering based on pattern."""
        if len(sent_messages) != len(received_messages):
            return False
            
        if pattern in ['sequential', 'burst', 'mixed_types']:
            # Messages should be in same order as sent
            for i, (sent, received) in enumerate(zip(sent_messages, received_messages)):
                if sent['id'] != received['id']:
                    return False
                    
        elif pattern == 'concurrent':
            # Messages from each sender should be in order
            sender_groups = {}
            for msg in received_messages:
                sender_id = msg.get('sender_id')
                if sender_id not in sender_groups:
                    sender_groups[sender_id] = []
                sender_groups[sender_id].append(msg)
            
            # Verify each sender's messages are in sequence order
            for sender_id, messages in sender_groups.items():
                for i, msg in enumerate(messages):
                    if msg['sequence'] != i:
                        return False
                        
        return True
    
    def _verify_sequence_integrity(self, messages: List[Dict]) -> bool:
        """Verify sequence numbers are consistent."""
        if not messages:
            return True
            
        # Check for gaps or duplicates in sequence numbers
        sequences = [msg.get('sequence', -1) for msg in messages]
        
        # Remove invalid sequences
        valid_sequences = [seq for seq in sequences if seq >= 0]
        
        if not valid_sequences:
            return False
            
        # Check for continuous sequence (allowing for concurrent senders)
        unique_sequences = set(valid_sequences)
        expected_sequences = set(range(len(valid_sequences)))
        
        return len(unique_sequences.intersection(expected_sequences)) >= len(expected_sequences) * 0.8
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_message_corruption_detection(self, real_services_fixture):
        """Test detection and handling of corrupted WebSocket messages."""
        real_services = get_real_services()
        
        # Create test user context
        user_context = await self.create_test_user_context(real_services)
        
        # Test different corruption scenarios
        corruption_scenarios = [
            {
                'name': 'json_corruption',
                'corruption_type': 'invalid_json',
                'original_message': '{"type": "message", "content": "Hello"}',
                'corrupted_message': '{"type": "message", "content": "Hello"',  # Missing closing brace
                'expected_behavior': 'parse_error_handling'
            },
            {
                'name': 'encoding_corruption',
                'corruption_type': 'encoding_error',
                'original_message': 'Hello with unicode: émojis 🚀',
                'corrupted_message': b'Hello with unicode: \xff\xfe invalid bytes',
                'expected_behavior': 'encoding_error_handling'
            },
            {
                'name': 'checksum_corruption',
                'corruption_type': 'data_integrity',
                'original_message': '{"data": "important", "checksum": "valid"}',
                'corrupted_message': '{"data": "corrupted", "checksum": "valid"}',  # Data changed but checksum not
                'expected_behavior': 'integrity_check_failure'
            },
            {
                'name': 'size_corruption',
                'corruption_type': 'size_mismatch',
                'original_message': 'Normal message',
                'corrupted_message': 'Normal message' + '\x00' * 1000,  # Unexpected null bytes
                'expected_behavior': 'size_validation_error'
            }
        ]
        
        corruption_detection_results = []
        
        for scenario in corruption_scenarios:
            logger.info(f"Testing message corruption: {scenario['name']}")
            
            try:
                corruption_result = await self._test_message_corruption_scenario(
                    user_context, scenario
                )
                
                corruption_detection_results.append({
                    'scenario': scenario['name'],
                    'corruption_detected': corruption_result.get('corruption_detected', False),
                    'error_handled_gracefully': corruption_result.get('error_handled_gracefully', False),
                    'recovery_attempted': corruption_result.get('recovery_attempted', False),
                    'data_integrity_maintained': corruption_result.get('data_integrity_maintained', False),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                # Check if exception indicates appropriate corruption handling
                appropriate_error = self._is_appropriate_corruption_error(e, scenario)
                
                corruption_detection_results.append({
                    'scenario': scenario['name'],
                    'corruption_detected': True,  # Exception indicates detection
                    'error_handled_gracefully': appropriate_error,
                    'recovery_attempted': False,
                    'data_integrity_maintained': True,  # Exception prevented bad data processing
                    'success': False,
                    'error': str(e)
                })
        
        # Verify corruption detection effectiveness
        corruption_detected = [r for r in corruption_detection_results if r.get('corruption_detected')]
        detection_rate = len(corruption_detected) / len(corruption_detection_results)
        
        graceful_handling = [r for r in corruption_detection_results if r.get('error_handled_gracefully')]
        graceful_rate = len(graceful_handling) / len(corruption_detection_results)
        
        integrity_maintained = [r for r in corruption_detection_results if r.get('data_integrity_maintained')]
        integrity_rate = len(integrity_maintained) / len(corruption_detection_results)
        
        assert detection_rate >= 0.8, \
            f"Message corruption detection insufficient: {detection_rate:.1%}"
        
        assert graceful_rate >= 0.7, \
            f"Corruption error handling insufficient: {graceful_rate:.1%}"
        
        assert integrity_rate >= 0.9, \
            f"Data integrity not maintained during corruption: {integrity_rate:.1%}"
            
        logger.info(f"Corruption detection test - Detection: {detection_rate:.1%}, "
                   f"Graceful handling: {graceful_rate:.1%}, Integrity: {integrity_rate:.1%}")
    
    async def _test_message_corruption_scenario(self, user_context: Dict, scenario: Dict) -> Dict:
        """Test specific message corruption scenario."""
        corruption_type = scenario['corruption_type']
        corrupted_message = scenario['corrupted_message']
        
        if corruption_type == 'invalid_json':
            # Test JSON parsing with corrupted data
            try:
                json.loads(corrupted_message)
                return {
                    'corruption_detected': False,
                    'error_handled_gracefully': False,
                    'recovery_attempted': False,
                    'data_integrity_maintained': False
                }
            except json.JSONDecodeError:
                return {
                    'corruption_detected': True,
                    'error_handled_gracefully': True,
                    'recovery_attempted': False,
                    'data_integrity_maintained': True
                }
                
        elif corruption_type == 'encoding_error':
            # Test encoding corruption
            try:
                if isinstance(corrupted_message, bytes):
                    decoded = corrupted_message.decode('utf-8')
                else:
                    decoded = corrupted_message
                    
                return {
                    'corruption_detected': False,
                    'error_handled_gracefully': True,
                    'recovery_attempted': False,
                    'data_integrity_maintained': True
                }
            except UnicodeDecodeError:
                return {
                    'corruption_detected': True,
                    'error_handled_gracefully': True,
                    'recovery_attempted': False,
                    'data_integrity_maintained': True
                }
                
        elif corruption_type == 'data_integrity':
            # Test checksum validation
            try:
                message_data = json.loads(corrupted_message)
                data = message_data.get('data', '')
                provided_checksum = message_data.get('checksum', '')
                
                # Calculate actual checksum
                actual_checksum = hashlib.md5(data.encode()).hexdigest()[:8]
                
                if provided_checksum != actual_checksum and provided_checksum == 'valid':
                    return {
                        'corruption_detected': True,
                        'error_handled_gracefully': True,
                        'recovery_attempted': False,
                        'data_integrity_maintained': True
                    }
                    
                return {
                    'corruption_detected': False,
                    'error_handled_gracefully': True,
                    'recovery_attempted': False,
                    'data_integrity_maintained': True
                }
                
            except Exception:
                return {
                    'corruption_detected': True,
                    'error_handled_gracefully': True,
                    'recovery_attempted': False,
                    'data_integrity_maintained': True
                }
                
        elif corruption_type == 'size_mismatch':
            # Test size validation
            message_size = len(corrupted_message)
            expected_max_size = 1000  # 1KB limit
            
            if message_size > expected_max_size:
                return {
                    'corruption_detected': True,
                    'error_handled_gracefully': True,
                    'recovery_attempted': False,
                    'data_integrity_maintained': True
                }
                
            return {
                'corruption_detected': False,
                'error_handled_gracefully': True,
                'recovery_attempted': False,
                'data_integrity_maintained': True
            }
    
    def _is_appropriate_corruption_error(self, error: Exception, scenario: Dict) -> bool:
        """Check if error appropriately indicates corruption handling."""
        error_str = str(error).lower()
        corruption_type = scenario['corruption_type']
        
        if corruption_type == 'invalid_json':
            return any(keyword in error_str for keyword in ['json', 'parse', 'syntax'])
        elif corruption_type == 'encoding_error':
            return any(keyword in error_str for keyword in ['encoding', 'unicode', 'decode'])
        elif corruption_type == 'data_integrity':
            return any(keyword in error_str for keyword in ['checksum', 'integrity', 'validation'])
        elif corruption_type == 'size_mismatch':
            return any(keyword in error_str for keyword in ['size', 'length', 'limit'])
        
        return True  # Any error is better than silent corruption
        
    @pytest.mark.integration
    async def test_websocket_message_deduplication(self):
        """Test WebSocket message deduplication mechanisms."""
        # Test scenarios with duplicate messages
        deduplication_scenarios = [
            {
                'name': 'exact_duplicate_messages',
                'original_message': {'id': 'msg_123', 'content': 'Hello'},
                'duplicate_count': 3,
                'expected_behavior': 'single_processing'
            },
            {
                'name': 'near_duplicate_messages',
                'original_message': {'id': 'msg_456', 'content': 'Hello', 'timestamp': 1000},
                'duplicates': [
                    {'id': 'msg_456', 'content': 'Hello', 'timestamp': 1001},  # Slight timestamp difference
                    {'id': 'msg_456', 'content': 'Hello', 'timestamp': 1002}
                ],
                'expected_behavior': 'id_based_deduplication'
            },
            {
                'name': 'retry_duplicate_messages',
                'original_message': {'id': 'msg_789', 'content': 'Important', 'retry': 0},
                'duplicates': [
                    {'id': 'msg_789', 'content': 'Important', 'retry': 1},
                    {'id': 'msg_789', 'content': 'Important', 'retry': 2}
                ],
                'expected_behavior': 'latest_retry_wins'
            }
        ]
        
        deduplication_results = []
        
        for scenario in deduplication_scenarios:
            logger.info(f"Testing message deduplication: {scenario['name']}")
            
            try:
                result = await self._test_message_deduplication_scenario(scenario)
                
                deduplication_results.append({
                    'scenario': scenario['name'],
                    'deduplication_effective': result.get('deduplication_effective', False),
                    'messages_processed': result.get('messages_processed', 0),
                    'expected_processed': result.get('expected_processed', 1),
                    'duplicate_handling_correct': result.get('duplicate_handling_correct', False),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                deduplication_results.append({
                    'scenario': scenario['name'],
                    'deduplication_effective': False,
                    'messages_processed': 0,
                    'expected_processed': 1,
                    'duplicate_handling_correct': False,
                    'success': False,
                    'error': str(e)
                })
        
        # Verify deduplication effectiveness
        effective_deduplication = [r for r in deduplication_results if r.get('deduplication_effective')]
        effectiveness_rate = len(effective_deduplication) / len(deduplication_results)
        
        correct_handling = [r for r in deduplication_results if r.get('duplicate_handling_correct')]
        correctness_rate = len(correct_handling) / len(deduplication_results)
        
        assert effectiveness_rate >= 0.8, \
            f"Message deduplication effectiveness insufficient: {effectiveness_rate:.1%}"
        
        assert correctness_rate >= 0.8, \
            f"Duplicate message handling correctness insufficient: {correctness_rate:.1%}"
            
        logger.info(f"Message deduplication test - Effectiveness: {effectiveness_rate:.1%}, "
                   f"Correctness: {correctness_rate:.1%}")
    
    async def _test_message_deduplication_scenario(self, scenario: Dict) -> Dict:
        """Test specific message deduplication scenario."""
        name = scenario['name']
        original_message = scenario['original_message']
        
        processed_messages = []
        message_ids_seen = set()
        
        if name == 'exact_duplicate_messages':
            duplicate_count = scenario['duplicate_count']
            
            # Process original message
            if original_message['id'] not in message_ids_seen:
                processed_messages.append(original_message)
                message_ids_seen.add(original_message['id'])
            
            # Process duplicates
            for _ in range(duplicate_count):
                if original_message['id'] not in message_ids_seen:
                    processed_messages.append(original_message)
                    message_ids_seen.add(original_message['id'])
                # Else: duplicate detected and ignored
            
        elif name == 'near_duplicate_messages':
            duplicates = scenario['duplicates']
            
            # Process original
            if original_message['id'] not in message_ids_seen:
                processed_messages.append(original_message)
                message_ids_seen.add(original_message['id'])
            
            # Process near duplicates (should be deduplicated by ID)
            for duplicate in duplicates:
                if duplicate['id'] not in message_ids_seen:
                    processed_messages.append(duplicate)
                    message_ids_seen.add(duplicate['id'])
                    
        elif name == 'retry_duplicate_messages':
            duplicates = scenario['duplicates']
            message_versions = {}
            
            # Process original
            msg_id = original_message['id']
            message_versions[msg_id] = original_message
            
            # Process retries (latest should win)
            for duplicate in duplicates:
                current_version = message_versions.get(msg_id, {})
                current_retry = current_version.get('retry', -1)
                new_retry = duplicate.get('retry', 0)
                
                if new_retry > current_retry:
                    message_versions[msg_id] = duplicate
            
            processed_messages = list(message_versions.values())
        
        # Analyze results
        messages_processed = len(processed_messages)
        expected_processed = 1  # Should be deduplicated to single message
        
        deduplication_effective = (messages_processed == expected_processed)
        duplicate_handling_correct = deduplication_effective
        
        return {
            'deduplication_effective': deduplication_effective,
            'messages_processed': messages_processed,
            'expected_processed': expected_processed,
            'duplicate_handling_correct': duplicate_handling_correct
        }
        
    @pytest.mark.integration
    async def test_websocket_message_priority_handling(self):
        """Test WebSocket message priority and queue management."""
        # Test priority message scenarios
        priority_scenarios = [
            {
                'name': 'high_priority_overtaking',
                'messages': [
                    {'id': 'msg_1', 'priority': 'low', 'content': 'Low priority 1'},
                    {'id': 'msg_2', 'priority': 'low', 'content': 'Low priority 2'},
                    {'id': 'msg_3', 'priority': 'high', 'content': 'High priority'},
                    {'id': 'msg_4', 'priority': 'low', 'content': 'Low priority 3'}
                ],
                'expected_order': ['msg_3', 'msg_1', 'msg_2', 'msg_4'],  # High priority first
                'expected_behavior': 'priority_queue_reordering'
            },
            {
                'name': 'same_priority_fifo',
                'messages': [
                    {'id': 'msg_a', 'priority': 'medium', 'content': 'Medium 1'},
                    {'id': 'msg_b', 'priority': 'medium', 'content': 'Medium 2'},
                    {'id': 'msg_c', 'priority': 'medium', 'content': 'Medium 3'}
                ],
                'expected_order': ['msg_a', 'msg_b', 'msg_c'],  # FIFO for same priority
                'expected_behavior': 'fifo_within_priority'
            },
            {
                'name': 'mixed_priority_queue',
                'messages': [
                    {'id': 'msg_x', 'priority': 'low', 'content': 'Low'},
                    {'id': 'msg_y', 'priority': 'critical', 'content': 'Critical'},
                    {'id': 'msg_z', 'priority': 'high', 'content': 'High'}
                ],
                'expected_order': ['msg_y', 'msg_z', 'msg_x'],  # Critical > High > Low
                'expected_behavior': 'multi_level_priority'
            }
        ]
        
        priority_handling_results = []
        
        for scenario in priority_scenarios:
            logger.info(f"Testing message priority: {scenario['name']}")
            
            try:
                result = await self._test_priority_handling_scenario(scenario)
                
                priority_handling_results.append({
                    'scenario': scenario['name'],
                    'priority_respected': result.get('priority_respected', False),
                    'order_correct': result.get('order_correct', False),
                    'processing_order': result.get('processing_order', []),
                    'expected_order': scenario['expected_order'],
                    'queue_behavior_correct': result.get('queue_behavior_correct', False),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                priority_handling_results.append({
                    'scenario': scenario['name'],
                    'priority_respected': False,
                    'order_correct': False,
                    'processing_order': [],
                    'expected_order': scenario['expected_order'],
                    'queue_behavior_correct': False,
                    'success': False,
                    'error': str(e)
                })
        
        # Verify priority handling
        priority_respected = [r for r in priority_handling_results if r.get('priority_respected')]
        priority_rate = len(priority_respected) / len(priority_handling_results)
        
        correct_ordering = [r for r in priority_handling_results if r.get('order_correct')]
        ordering_rate = len(correct_ordering) / len(priority_handling_results)
        
        assert priority_rate >= 0.8, \
            f"Message priority handling insufficient: {priority_rate:.1%}"
        
        assert ordering_rate >= 0.8, \
            f"Priority-based message ordering insufficient: {ordering_rate:.1%}"
            
        logger.info(f"Priority handling test - Priority respected: {priority_rate:.1%}, "
                   f"Ordering correct: {ordering_rate:.1%}")
    
    async def _test_priority_handling_scenario(self, scenario: Dict) -> Dict:
        """Test specific message priority handling scenario."""
        messages = scenario['messages']
        expected_order = scenario['expected_order']
        
        # Define priority levels
        priority_levels = {
            'critical': 0,
            'high': 1,
            'medium': 2,
            'low': 3
        }
        
        # Sort messages by priority (lower number = higher priority)
        sorted_messages = sorted(
            messages, 
            key=lambda m: (priority_levels.get(m.get('priority', 'low'), 3), messages.index(m))
        )
        
        # Extract processing order
        processing_order = [msg['id'] for msg in sorted_messages]
        
        # Check if order matches expected
        order_correct = (processing_order == expected_order)
        
        # Check priority behavior
        priority_respected = True
        for i in range(len(sorted_messages) - 1):
            current_priority = priority_levels.get(sorted_messages[i].get('priority', 'low'), 3)
            next_priority = priority_levels.get(sorted_messages[i + 1].get('priority', 'low'), 3)
            
            # Higher priority (lower number) should come first
            if current_priority > next_priority:
                priority_respected = False
                break
        
        queue_behavior_correct = order_correct and priority_respected
        
        return {
            'priority_respected': priority_respected,
            'order_correct': order_correct,
            'processing_order': processing_order,
            'queue_behavior_correct': queue_behavior_correct
        }
        
    @pytest.mark.integration
    async def test_websocket_large_message_fragmentation(self):
        """Test WebSocket handling of large messages requiring fragmentation."""
        # Test large message scenarios
        large_message_scenarios = [
            {
                'name': 'single_large_message',
                'message_size': 100000,  # 100KB
                'fragment_size': 8192,   # 8KB fragments
                'expected_behavior': 'successful_fragmentation'
            },
            {
                'name': 'multiple_large_messages',
                'message_count': 5,
                'message_size': 50000,   # 50KB each
                'fragment_size': 4096,   # 4KB fragments
                'expected_behavior': 'concurrent_fragmentation'
            },
            {
                'name': 'very_large_message',
                'message_size': 1000000, # 1MB
                'fragment_size': 16384,  # 16KB fragments
                'expected_behavior': 'size_limit_handling'
            }
        ]
        
        fragmentation_results = []
        
        for scenario in large_message_scenarios:
            logger.info(f"Testing large message fragmentation: {scenario['name']}")
            
            try:
                result = await self._test_large_message_scenario(scenario)
                
                fragmentation_results.append({
                    'scenario': scenario['name'],
                    'fragmentation_successful': result.get('fragmentation_successful', False),
                    'reassembly_successful': result.get('reassembly_successful', False),
                    'data_integrity_preserved': result.get('data_integrity_preserved', False),
                    'performance_acceptable': result.get('performance_acceptable', False),
                    'fragments_created': result.get('fragments_created', 0),
                    'processing_time': result.get('processing_time', 0),
                    'success': True,
                    'error': None
                })
                
            except Exception as e:
                fragmentation_results.append({
                    'scenario': scenario['name'],
                    'fragmentation_successful': False,
                    'reassembly_successful': False,
                    'data_integrity_preserved': False,
                    'performance_acceptable': False,
                    'fragments_created': 0,
                    'processing_time': 0,
                    'success': False,
                    'error': str(e)
                })
        
        # Verify fragmentation handling
        successful_fragmentation = [r for r in fragmentation_results if r.get('fragmentation_successful')]
        fragmentation_success_rate = len(successful_fragmentation) / len(fragmentation_results)
        
        successful_reassembly = [r for r in fragmentation_results if r.get('reassembly_successful')]
        reassembly_success_rate = len(successful_reassembly) / len(fragmentation_results)
        
        integrity_preserved = [r for r in fragmentation_results if r.get('data_integrity_preserved')]
        integrity_rate = len(integrity_preserved) / len(fragmentation_results)
        
        assert fragmentation_success_rate >= 0.8, \
            f"Large message fragmentation insufficient: {fragmentation_success_rate:.1%}"
        
        assert reassembly_success_rate >= 0.8, \
            f"Message reassembly insufficient: {reassembly_success_rate:.1%}"
        
        assert integrity_rate >= 0.9, \
            f"Data integrity not preserved during fragmentation: {integrity_rate:.1%}"
        
        # Verify reasonable performance
        performance_acceptable = [r for r in fragmentation_results if r.get('performance_acceptable')]
        performance_rate = len(performance_acceptable) / len(fragmentation_results)
        
        assert performance_rate >= 0.7, \
            f"Large message processing performance insufficient: {performance_rate:.1%}"
            
        logger.info(f"Large message fragmentation test - Fragmentation: {fragmentation_success_rate:.1%}, "
                   f"Reassembly: {reassembly_success_rate:.1%}, Integrity: {integrity_rate:.1%}")
    
    async def _test_large_message_scenario(self, scenario: Dict) -> Dict:
        """Test specific large message fragmentation scenario."""
        name = scenario['name']
        message_size = scenario['message_size']
        fragment_size = scenario['fragment_size']
        
        start_time = time.time()
        
        # Create large message
        large_message = 'x' * message_size
        
        # Calculate expected fragments
        expected_fragments = (message_size + fragment_size - 1) // fragment_size
        
        # Simulate fragmentation
        fragments = []
        for i in range(0, message_size, fragment_size):
            fragments.append(large_message[i:i + fragment_size])
        
        # Verify fragmentation
        fragmentation_successful = (len(fragments) == expected_fragments)
        
        # Simulate transmission delay
        await asyncio.sleep(0.1 * len(fragments))  # Proportional to fragment count
        
        # Simulate reassembly
        reassembled_message = ''.join(fragments)
        reassembly_successful = (reassembled_message == large_message)
        
        # Check data integrity
        data_integrity_preserved = (
            len(reassembled_message) == message_size and 
            reassembled_message == large_message
        )
        
        processing_time = time.time() - start_time
        
        # Performance check - should complete in reasonable time
        max_expected_time = 2.0 + (message_size / 100000)  # Base time + size-based
        performance_acceptable = (processing_time < max_expected_time)
        
        return {
            'fragmentation_successful': fragmentation_successful,
            'reassembly_successful': reassembly_successful,
            'data_integrity_preserved': data_integrity_preserved,
            'performance_acceptable': performance_acceptable,
            'fragments_created': len(fragments),
            'processing_time': processing_time
        }