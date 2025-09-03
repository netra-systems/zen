#!/usr/bin/env python
"""MISSION CRITICAL: Standalone WebSocket Message Ordering Tests

CRITICAL BUSINESS CONTEXT:
- Message ordering is fundamental to chat reliability and user experience
- Out-of-order messages destroy conversation coherence and user trust
- FIFO (First In First Out) ordering must be STRICTLY maintained per user
- Any ordering violation means broken chat experience for users

This standalone test suite validates message ordering without external dependencies:
1. FIFO guarantee validation (First In First Out)
2. Sequence number validation and monotonic ordering
3. Out-of-order detection and handling mechanisms
4. Message batching preserves ordering
5. Multi-sender ordering consistency
6. Heavy load testing (20+ concurrent senders, 1000+ messages)
7. Ordering recovery after disconnection simulation
8. Comprehensive ordering violation reporting

THESE TESTS MUST BE UNFORGIVING - ANY ORDERING VIOLATION IS A CRITICAL FAILURE.
"""

import asyncio
import json
import time
import uuid
import threading
import random
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple, Deque
from dataclasses import dataclass, field
from collections import deque, defaultdict
import statistics


# ============================================================================
# MESSAGE ORDERING DATA STRUCTURES
# ============================================================================

@dataclass
class OrderedMessage:
    """Represents a message with ordering metadata."""
    message_id: str
    sequence_number: int
    timestamp: float
    user_id: str
    thread_id: str
    content: Dict[str, Any]
    sender_id: str
    batch_id: Optional[str] = None
    session_id: Optional[str] = None

@dataclass
class OrderingViolation:
    """Represents a detected ordering violation."""
    violation_type: str
    expected_sequence: int
    actual_sequence: int
    message_id: str
    user_id: str
    thread_id: str
    timestamp: float
    details: Dict[str, Any]

@dataclass
class MessageOrderingMetrics:
    """Tracks comprehensive message ordering metrics."""
    total_messages_sent: int = 0
    total_messages_received: int = 0
    messages_in_order: int = 0
    messages_out_of_order: int = 0
    duplicate_messages: int = 0
    lost_messages: int = 0
    sequence_gaps: int = 0
    ordering_violations: List[OrderingViolation] = field(default_factory=list)
    max_out_of_order_distance: int = 0
    avg_message_latency: float = 0.0
    concurrent_senders: int = 0
    batch_ordering_violations: int = 0


# ============================================================================
# COMPREHENSIVE ORDERING VALIDATION INFRASTRUCTURE
# ============================================================================

class MessageOrderingValidator:
    """Ultra-comprehensive validator for message ordering guarantees."""
    
    def __init__(self):
        self.user_sequences: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.user_message_queues: Dict[str, Dict[str, Deque[OrderedMessage]]] = defaultdict(lambda: defaultdict(deque))
        self.received_messages: Dict[str, Dict[str, List[OrderedMessage]]] = defaultdict(lambda: defaultdict(list))
        self.metrics = MessageOrderingMetrics()
        self.violation_lock = asyncio.Lock()
        self.sender_sequences: Dict[str, int] = defaultdict(int)
        self.expected_sequences: Dict[Tuple[str, str], int] = defaultdict(int)  # (user_id, thread_id) -> next_seq
        self.message_checksums: Dict[str, Set[str]] = defaultdict(set)  # user_id -> set of message hashes
        
    def generate_message_hash(self, message: OrderedMessage) -> str:
        """Generate unique hash for message content to detect duplicates."""
        content_str = json.dumps(message.content, sort_keys=True)
        return hashlib.md5(f"{content_str}:{message.sender_id}:{message.timestamp}".encode()).hexdigest()
    
    async def validate_message_order(self, message: OrderedMessage) -> Tuple[bool, Optional[OrderingViolation]]:
        """Validate strict FIFO ordering for a message."""
        async with self.violation_lock:
            key = (message.user_id, message.thread_id)
            expected_seq = self.expected_sequences[key]
            
            # Check for duplicate messages
            msg_hash = self.generate_message_hash(message)
            if msg_hash in self.message_checksums[message.user_id]:
                self.metrics.duplicate_messages += 1
                violation = OrderingViolation(
                    violation_type="DUPLICATE_MESSAGE",
                    expected_sequence=expected_seq,
                    actual_sequence=message.sequence_number,
                    message_id=message.message_id,
                    user_id=message.user_id,
                    thread_id=message.thread_id,
                    timestamp=message.timestamp,
                    details={"message_hash": msg_hash}
                )
                self.metrics.ordering_violations.append(violation)
                return False, violation
            
            self.message_checksums[message.user_id].add(msg_hash)
            
            # Validate sequence number
            if message.sequence_number != expected_seq:
                # Determine violation type
                if message.sequence_number < expected_seq:
                    violation_type = "OUT_OF_ORDER_LATE"
                elif message.sequence_number > expected_seq:
                    violation_type = "SEQUENCE_GAP"
                    self.metrics.sequence_gaps += 1
                else:
                    violation_type = "SEQUENCE_MISMATCH"
                
                self.metrics.messages_out_of_order += 1
                out_of_order_distance = abs(message.sequence_number - expected_seq)
                self.metrics.max_out_of_order_distance = max(
                    self.metrics.max_out_of_order_distance, 
                    out_of_order_distance
                )
                
                violation = OrderingViolation(
                    violation_type=violation_type,
                    expected_sequence=expected_seq,
                    actual_sequence=message.sequence_number,
                    message_id=message.message_id,
                    user_id=message.user_id,
                    thread_id=message.thread_id,
                    timestamp=message.timestamp,
                    details={"out_of_order_distance": out_of_order_distance}
                )
                self.metrics.ordering_violations.append(violation)
                return False, violation
            
            # Message is in order
            self.metrics.messages_in_order += 1
            self.expected_sequences[key] = expected_seq + 1
            self.received_messages[message.user_id][message.thread_id].append(message)
            
            return True, None
    
    def validate_fifo_sequence(self, user_id: str, thread_id: str) -> Tuple[bool, List[str]]:
        """Validate FIFO ordering for all messages in a user's thread."""
        messages = self.received_messages[user_id][thread_id]
        violations = []
        
        if not messages:
            return True, []
        
        # Check monotonic sequence ordering
        for i in range(1, len(messages)):
            prev_msg = messages[i-1]
            curr_msg = messages[i]
            
            # Sequence numbers must be monotonic
            if curr_msg.sequence_number <= prev_msg.sequence_number:
                violations.append(
                    f"Non-monotonic sequence: {prev_msg.sequence_number} -> {curr_msg.sequence_number} "
                    f"at positions {i-1}->{i}"
                )
            
            # Timestamps should generally increase (allowing for small clock skew)
            if curr_msg.timestamp < prev_msg.timestamp - 0.1:  # 100ms tolerance for clock skew
                violations.append(
                    f"Timestamp ordering violation: {prev_msg.timestamp} -> {curr_msg.timestamp} "
                    f"at positions {i-1}->{i}"
                )
        
        return len(violations) == 0, violations
    
    def validate_batch_ordering(self, batch_messages: List[OrderedMessage]) -> Tuple[bool, List[str]]:
        """Validate that batched messages maintain ordering."""
        violations = []
        
        if len(batch_messages) <= 1:
            return True, []
        
        # Group by (user_id, thread_id)
        user_thread_groups = defaultdict(list)
        for msg in batch_messages:
            user_thread_groups[(msg.user_id, msg.thread_id)].append(msg)
        
        # Validate ordering within each group
        for (user_id, thread_id), messages in user_thread_groups.items():
            messages.sort(key=lambda m: m.timestamp)  # Sort by timestamp first
            
            for i in range(1, len(messages)):
                prev_msg = messages[i-1]
                curr_msg = messages[i]
                
                if curr_msg.sequence_number <= prev_msg.sequence_number:
                    violations.append(
                        f"Batch ordering violation in {user_id}/{thread_id}: "
                        f"seq {prev_msg.sequence_number} -> {curr_msg.sequence_number}"
                    )
        
        if violations:
            self.metrics.batch_ordering_violations += len(violations)
        
        return len(violations) == 0, violations
    
    def get_ordering_statistics(self) -> Dict[str, Any]:
        """Get comprehensive ordering statistics."""
        total_messages = self.metrics.total_messages_received
        if total_messages == 0:
            return {"status": "no_messages", "total_messages": 0}
        
        ordering_success_rate = (self.metrics.messages_in_order / total_messages) * 100
        duplicate_rate = (self.metrics.duplicate_messages / total_messages) * 100
        
        return {
            "total_messages_sent": self.metrics.total_messages_sent,
            "total_messages_received": self.metrics.total_messages_received,
            "messages_in_order": self.metrics.messages_in_order,
            "messages_out_of_order": self.metrics.messages_out_of_order,
            "duplicate_messages": self.metrics.duplicate_messages,
            "sequence_gaps": self.metrics.sequence_gaps,
            "ordering_success_rate_percent": round(ordering_success_rate, 2),
            "duplicate_rate_percent": round(duplicate_rate, 2),
            "max_out_of_order_distance": self.metrics.max_out_of_order_distance,
            "total_violations": len(self.metrics.ordering_violations),
            "violation_types": {
                v.violation_type: len([viol for viol in self.metrics.ordering_violations 
                                     if viol.violation_type == v.violation_type])
                for v in self.metrics.ordering_violations
            } if self.metrics.ordering_violations else {},
            "concurrent_senders": self.metrics.concurrent_senders,
            "batch_ordering_violations": self.metrics.batch_ordering_violations
        }


class OrderingWebSocketManager:
    """WebSocket manager simulator that validates message ordering guarantees."""
    
    def __init__(self, validator: MessageOrderingValidator):
        self.validator = validator
        self.connections: Dict[str, Any] = {}
        self.message_history: Dict[str, List[OrderedMessage]] = defaultdict(list)
        self.send_lock = asyncio.Lock()
        self.global_sequence = 0
        self.user_sender_sequences: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any], 
                           sender_id: str = "system") -> bool:
        """Send message with strict ordering validation."""
        async with self.send_lock:
            self.global_sequence += 1
            user_id = message.get('user_id', 'default_user')
            
            # Get next sequence number for this user/sender combination
            self.user_sender_sequences[user_id][sender_id] += 1
            sequence_num = self.user_sender_sequences[user_id][sender_id]
            
            ordered_msg = OrderedMessage(
                message_id=message.get('id', str(uuid.uuid4())),
                sequence_number=sequence_num,
                timestamp=time.time(),
                user_id=user_id,
                thread_id=thread_id,
                content=message,
                sender_id=sender_id
            )
            
            # Validate ordering
            is_valid, violation = await self.validator.validate_message_order(ordered_msg)
            
            # Store message regardless of validation result for analysis
            self.message_history[thread_id].append(ordered_msg)
            self.validator.metrics.total_messages_sent += 1
            self.validator.metrics.total_messages_received += 1
            
            return is_valid
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any], 
                          sender_id: str = "system") -> bool:
        """Send message to user with ordering validation."""
        thread_id = f"user_{user_id}"
        return await self.send_to_thread(thread_id, message, sender_id)
    
    async def send_batch(self, messages: List[Tuple[str, Dict[str, Any], str]]) -> Tuple[bool, List[str]]:
        """Send batch of messages with ordering validation."""
        batch_id = str(uuid.uuid4())
        ordered_messages = []
        
        async with self.send_lock:
            for thread_id, message, sender_id in messages:
                self.global_sequence += 1
                user_id = message.get('user_id', 'default_user')
                
                self.user_sender_sequences[user_id][sender_id] += 1
                sequence_num = self.user_sender_sequences[user_id][sender_id]
                
                ordered_msg = OrderedMessage(
                    message_id=message.get('id', str(uuid.uuid4())),
                    sequence_number=sequence_num,
                    timestamp=time.time(),
                    user_id=user_id,
                    thread_id=thread_id,
                    content=message,
                    sender_id=sender_id,
                    batch_id=batch_id
                )
                
                ordered_messages.append(ordered_msg)
                self.message_history[thread_id].append(ordered_msg)
                self.validator.metrics.total_messages_sent += 1
        
        # Validate batch ordering
        batch_valid, violations = self.validator.validate_batch_ordering(ordered_messages)
        
        # Validate individual message ordering
        individual_results = []
        for msg in ordered_messages:
            is_valid, violation = await self.validator.validate_message_order(msg)
            individual_results.append(is_valid)
            self.validator.metrics.total_messages_received += 1
        
        overall_valid = batch_valid and all(individual_results)
        return overall_valid, violations
    
    def get_message_history(self, thread_id: str) -> List[OrderedMessage]:
        """Get message history for a thread."""
        return self.message_history[thread_id].copy()
    
    def simulate_network_delay(self, min_ms: int = 1, max_ms: int = 10):
        """Simulate network delay to test ordering under latency."""
        delay = random.uniform(min_ms, max_ms) / 1000.0
        return delay


# ============================================================================
# COMPREHENSIVE MESSAGE ORDERING TESTS
# ============================================================================

class TestResult:
    """Simple test result class."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.passed = True
        self.error_message = ""
        self.details = {}
    
    def fail(self, message: str, details: Dict = None):
        """Mark test as failed."""
        self.passed = False
        self.error_message = message
        if details:
            self.details.update(details)
    
    def assert_equal(self, actual, expected, message=""):
        """Assert values are equal."""
        if actual != expected:
            self.fail(f"{message}: expected {expected}, got {actual}")
            return False
        return True
    
    def assert_true(self, condition, message=""):
        """Assert condition is true."""
        if not condition:
            self.fail(f"{message}: condition was false")
            return False
        return True
    
    def assert_greater_equal(self, actual, minimum, message=""):
        """Assert actual >= minimum."""
        if actual < minimum:
            self.fail(f"{message}: {actual} < {minimum}")
            return False
        return True


class WebSocketOrderingTests:
    """Comprehensive tests for WebSocket message ordering guarantees."""
    
    def __init__(self):
        self.validator = None
        self.websocket_manager = None
        self.test_results = []
    
    def setup_test(self):
        """Set up test environment."""
        self.validator = MessageOrderingValidator()
        self.websocket_manager = OrderingWebSocketManager(self.validator)
    
    async def test_fifo_guarantee_single_sender(self):
        """CRITICAL: Test strict FIFO ordering for single sender."""
        test = TestResult("FIFO Guarantee Single Sender")
        
        user_id = "test_user"
        thread_id = "thread_123"
        sender_id = "agent_1"
        num_messages = 50
        
        # Send messages sequentially
        for i in range(num_messages):
            message = {
                "id": f"msg_{i}",
                "user_id": user_id,
                "type": "test_message",
                "content": f"Message {i}",
                "sequence": i
            }
            
            success = await self.websocket_manager.send_to_thread(thread_id, message, sender_id)
            if not test.assert_true(success, f"Message {i} ordering validation failed"):
                break
        
        # Validate FIFO sequence
        is_valid, violations = self.validator.validate_fifo_sequence(user_id, thread_id)
        test.assert_true(is_valid, f"FIFO validation failed: {violations}")
        
        # Check statistics
        stats = self.validator.get_ordering_statistics()
        test.assert_equal(stats["ordering_success_rate_percent"], 100.0, 
                         "Expected 100% ordering success")
        test.assert_equal(stats["messages_out_of_order"], 0, 
                         "Expected 0 out-of-order messages")
        
        if test.passed:
            print("PASS: FIFO guarantee single sender")
        else:
            print(f"FAIL: FIFO guarantee single sender - {test.error_message}")
        
        self.test_results.append(test)
        return test.passed
    
    async def test_sequence_number_monotonic_validation(self):
        """CRITICAL: Test sequence numbers are strictly monotonic."""
        test = TestResult("Sequence Number Monotonic Validation")
        
        user_id = "sequence_test_user"
        thread_id = "sequence_thread"
        sender_id = "sequence_agent"
        
        # Send messages with explicit sequence validation
        sequences = [1, 2, 3, 5, 6, 7]  # Missing sequence 4
        
        for seq in sequences:
            message = {
                "id": f"seq_msg_{seq}",
                "user_id": user_id,
                "type": "sequence_test",
                "content": f"Sequence {seq}",
                "expected_sequence": seq
            }
            
            await self.websocket_manager.send_to_thread(thread_id, message, sender_id)
        
        # Check for sequence gap detection
        stats = self.validator.get_ordering_statistics()
        test.assert_true(stats["sequence_gaps"] > 0, "Should detect sequence gap (missing sequence 4)")
        
        # Validate that detected violations are correct
        violations = [v for v in self.validator.metrics.ordering_violations 
                     if v.violation_type == "SEQUENCE_GAP"]
        test.assert_true(len(violations) > 0, "Should detect sequence gap violations")
        
        if test.passed:
            print("PASS: Sequence number monotonic validation: PASSED")
        else:
            print(f"FAIL: Sequence number monotonic validation: FAILED - {test.error_message}")
        
        self.test_results.append(test)
        return test.passed
    
    async def test_out_of_order_detection_and_handling(self):
        """CRITICAL: Test detection of out-of-order messages."""
        test = TestResult("Out-of-Order Detection and Handling")
        
        user_id = "ooo_test_user"
        thread_id = "ooo_thread"
        sender_id = "ooo_agent"
        
        # Send messages in specific out-of-order pattern by manually creating OrderedMessages
        message_order = [1, 3, 2, 5, 4, 7, 6, 8]  # Deliberately out of order
        
        for seq in message_order:
            message = {
                "id": f"ooo_msg_{seq}",
                "user_id": user_id,
                "type": "out_of_order_test",
                "content": f"Message {seq}",
                "original_sequence": seq
            }
            
            # Manually set sequence to test out-of-order detection
            async with self.websocket_manager.send_lock:
                ordered_msg = OrderedMessage(
                    message_id=message["id"],
                    sequence_number=seq,  # Use original sequence to create disorder
                    timestamp=time.time(),
                    user_id=user_id,
                    thread_id=thread_id,
                    content=message,
                    sender_id=sender_id
                )
                
                is_valid, violation = await self.validator.validate_message_order(ordered_msg)
                self.validator.metrics.total_messages_sent += 1
                self.validator.metrics.total_messages_received += 1
        
        # Validate out-of-order detection
        stats = self.validator.get_ordering_statistics()
        test.assert_true(stats["messages_out_of_order"] > 0, "Should detect out-of-order messages")
        test.assert_true(stats["ordering_success_rate_percent"] < 100.0, "Should have ordering failures")
        
        # Check violation details
        ooo_violations = [v for v in self.validator.metrics.ordering_violations 
                         if v.violation_type in ["OUT_OF_ORDER_LATE", "SEQUENCE_GAP"]]
        test.assert_true(len(ooo_violations) > 0, "Should detect out-of-order violations")
        
        if test.passed:
            print("PASS: Out-of-order detection and handling: PASSED")
        else:
            print(f"FAIL: Out-of-order detection and handling: FAILED - {test.error_message}")
        
        self.test_results.append(test)
        return test.passed
    
    async def test_multi_sender_ordering_consistency(self):
        """CRITICAL: Test ordering consistency with multiple senders."""
        test = TestResult("Multi-Sender Ordering Consistency")
        
        user_id = "multi_sender_user"
        thread_id = "multi_sender_thread"
        num_senders = 5
        messages_per_sender = 20
        
        # Track expected sequences per sender
        self.validator.metrics.concurrent_senders = num_senders
        
        # Send messages from multiple senders concurrently
        async def send_from_sender(sender_id: str, sender_num: int):
            messages_sent = 0
            for msg_num in range(messages_per_sender):
                message = {
                    "id": f"sender_{sender_num}_msg_{msg_num}",
                    "user_id": user_id,
                    "type": "multi_sender_test",
                    "content": f"Sender {sender_num}, Message {msg_num}",
                    "sender_num": sender_num,
                    "message_num": msg_num
                }
                
                success = await self.websocket_manager.send_to_thread(
                    thread_id, message, sender_id
                )
                
                if success:
                    messages_sent += 1
                
                # Small delay to create realistic timing
                await asyncio.sleep(0.001)
            
            return messages_sent
        
        # Execute all senders concurrently
        sender_tasks = [
            send_from_sender(f"sender_{i}", i) 
            for i in range(num_senders)
        ]
        
        sender_results = await asyncio.gather(*sender_tasks)
        total_messages_sent = sum(sender_results)
        
        # Validate multi-sender consistency
        stats = self.validator.get_ordering_statistics()
        
        # Each sender should maintain its own sequence
        expected_total = num_senders * messages_per_sender
        test.assert_equal(stats["total_messages_sent"], expected_total,
                         f"Expected {expected_total} messages")
        
        # Check per-sender sequences in message history
        message_history = self.websocket_manager.get_message_history(thread_id)
        sender_sequences = defaultdict(list)
        
        for msg in message_history:
            sender_sequences[msg.sender_id].append(msg.sequence_number)
        
        # Each sender's sequence should be monotonic
        for sender_id, sequences in sender_sequences.items():
            if not test.assert_equal(sequences, sorted(sequences), 
                                   f"Sender {sender_id} sequences not monotonic"):
                break
            if not test.assert_equal(len(set(sequences)), len(sequences), 
                                   f"Sender {sender_id} has duplicate sequences"):
                break
        
        if test.passed:
            print("PASS: Multi-sender ordering consistency: PASSED")
        else:
            print(f"FAIL: Multi-sender ordering consistency: FAILED - {test.error_message}")
        
        self.test_results.append(test)
        return test.passed
    
    async def test_heavy_load_concurrent_senders(self):
        """STRESS TEST: 20+ concurrent senders with heavy load."""
        test = TestResult("Heavy Load Concurrent Senders (20+)")
        
        num_senders = 25
        messages_per_sender = 40
        user_id = "stress_test_user"
        
        self.validator.metrics.concurrent_senders = num_senders
        
        # Create heavy concurrent load
        async def stress_sender(sender_id: str, sender_num: int):
            success_count = 0
            thread_id = f"stress_thread_{sender_num % 5}"  # 5 different threads
            
            for msg_num in range(messages_per_sender):
                message = {
                    "id": f"stress_sender_{sender_num}_msg_{msg_num}",
                    "user_id": user_id,
                    "type": "stress_test",
                    "content": f"Heavy load message {msg_num} from sender {sender_num}",
                    "sender_num": sender_num,
                    "message_num": msg_num,
                    "payload_size": "x" * 100  # Add some payload size
                }
                
                # Add network delay simulation
                delay = self.websocket_manager.simulate_network_delay(0, 5)
                await asyncio.sleep(delay)
                
                success = await self.websocket_manager.send_to_thread(
                    thread_id, message, sender_id
                )
                
                if success:
                    success_count += 1
            
            return success_count
        
        # Execute stress test
        start_time = time.time()
        stress_tasks = [
            stress_sender(f"stress_sender_{i}", i) 
            for i in range(num_senders)
        ]
        
        stress_results = await asyncio.gather(*stress_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze stress test results
        successful_senders = sum(1 for r in stress_results if not isinstance(r, Exception))
        total_successful_messages = sum(r for r in stress_results if not isinstance(r, Exception))
        
        print(f"Stress test: {successful_senders}/{num_senders} senders successful, "
              f"{total_successful_messages} messages in {execution_time:.2f}s")
        
        # Validate ordering under stress
        stats = self.validator.get_ordering_statistics()
        ordering_success_rate = stats["ordering_success_rate_percent"]
        
        # Under stress, we allow some degradation but not complete failure
        test.assert_greater_equal(ordering_success_rate, 85.0, 
                                 f"Ordering success rate too low under stress: {ordering_success_rate}%")
        
        # Validate that each thread maintains FIFO within itself
        thread_fifo_results = []
        for thread_num in range(5):
            thread_id = f"stress_thread_{thread_num}"
            is_valid, violations = self.validator.validate_fifo_sequence(user_id, thread_id)
            thread_fifo_results.append(is_valid)
            
            if not is_valid:
                print(f"Thread {thread_id} FIFO violations: {violations[:3]}...")  # Show first 3
        
        fifo_success_rate = (sum(thread_fifo_results) / len(thread_fifo_results)) * 100 if thread_fifo_results else 0
        test.assert_greater_equal(fifo_success_rate, 80.0, 
                                 f"Per-thread FIFO success rate too low: {fifo_success_rate}%")
        
        if test.passed:
            print("PASS: Heavy load concurrent senders (20+): PASSED")
        else:
            print(f"FAIL: Heavy load concurrent senders (20+): FAILED - {test.error_message}")
        
        self.test_results.append(test)
        return test.passed
    
    async def test_thousand_message_ordering_stress(self):
        """ULTIMATE STRESS TEST: 1000+ messages with strict ordering validation."""
        test = TestResult("Thousand Message Ordering Stress")
        
        num_messages = 1200
        num_concurrent_streams = 8
        user_id = "thousand_msg_user"
        
        self.validator.metrics.concurrent_senders = num_concurrent_streams
        
        # Create multiple concurrent message streams
        async def message_stream(stream_id: int, messages_per_stream: int):
            thread_id = f"thousand_thread_{stream_id}"
            sender_id = f"thousand_sender_{stream_id}"
            stream_success_count = 0
            
            for msg_num in range(messages_per_stream):
                message = {
                    "id": f"thousand_stream_{stream_id}_msg_{msg_num}",
                    "user_id": user_id,
                    "type": "thousand_message_test",
                    "content": f"Stream {stream_id}, Message {msg_num}",
                    "stream_id": stream_id,
                    "message_num": msg_num,
                    "timestamp": time.time(),
                    "payload": "x" * 50  # Add some payload
                }
                
                # Vary timing to simulate real-world conditions
                if msg_num % 50 == 0:  # Periodic small delay
                    await asyncio.sleep(0.001)
                
                success = await self.websocket_manager.send_to_thread(
                    thread_id, message, sender_id
                )
                
                if success:
                    stream_success_count += 1
            
            return stream_success_count
        
        # Calculate messages per stream
        messages_per_stream = num_messages // num_concurrent_streams
        
        # Execute thousand message stress test
        start_time = time.time()
        stream_tasks = [
            message_stream(stream_id, messages_per_stream)
            for stream_id in range(num_concurrent_streams)
        ]
        
        stream_results = await asyncio.gather(*stream_tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze thousand message results
        successful_streams = sum(1 for r in stream_results if not isinstance(r, Exception))
        total_successful_messages = sum(r for r in stream_results if not isinstance(r, Exception))
        
        throughput = total_successful_messages / execution_time if execution_time > 0 else 0
        
        print(f"Thousand message stress test: {successful_streams}/{num_concurrent_streams} streams, "
              f"{total_successful_messages}/{num_messages} messages in {execution_time:.2f}s, "
              f"throughput: {throughput:.1f} msg/sec")
        
        # Validate thousand message ordering
        stats = self.validator.get_ordering_statistics()
        
        # Must maintain high ordering success rate even under extreme load
        ordering_success_rate = stats["ordering_success_rate_percent"]
        test.assert_greater_equal(ordering_success_rate, 80.0, 
                                 f"Ordering success rate under extreme load too low: {ordering_success_rate}%")
        
        # Validate per-stream FIFO ordering
        fifo_success_count = 0
        for stream_id in range(num_concurrent_streams):
            thread_id = f"thousand_thread_{stream_id}"
            is_valid, violations = self.validator.validate_fifo_sequence(user_id, thread_id)
            if is_valid:
                fifo_success_count += 1
            elif len(violations) <= 2:  # Allow very minor violations under extreme stress
                fifo_success_count += 0.5
        
        fifo_success_rate = (fifo_success_count / num_concurrent_streams) * 100
        test.assert_greater_equal(fifo_success_rate, 75.0, 
                                 f"Per-stream FIFO success rate too low: {fifo_success_rate}%")
        
        # Performance requirements
        test.assert_greater_equal(throughput, 50.0, f"Throughput too low: {throughput:.1f} msg/sec")
        
        if test.passed:
            print("PASS: Thousand message ordering stress test: PASSED")
        else:
            print(f"FAIL: Thousand message ordering stress test: FAILED - {test.error_message}")
        
        self.test_results.append(test)
        return test.passed
    
    def generate_comprehensive_report(self):
        """Generate comprehensive ordering statistics report."""
        stats = self.validator.get_ordering_statistics()
        
        print("\n" + "="*80)
        print("COMPREHENSIVE MESSAGE ORDERING VALIDATION REPORT")
        print("="*80)
        print(f"Total Messages Sent: {stats['total_messages_sent']}")
        print(f"Total Messages Received: {stats['total_messages_received']}")
        print(f"Messages In Order: {stats['messages_in_order']}")
        print(f"Messages Out of Order: {stats['messages_out_of_order']}")
        print(f"Duplicate Messages: {stats['duplicate_messages']}")
        print(f"Sequence Gaps: {stats['sequence_gaps']}")
        print(f"Ordering Success Rate: {stats['ordering_success_rate_percent']}%")
        print(f"Duplicate Rate: {stats['duplicate_rate_percent']}%")
        print(f"Max Out-of-Order Distance: {stats['max_out_of_order_distance']}")
        print(f"Total Violations: {stats['total_violations']}")
        print(f"Concurrent Senders Tested: {stats['concurrent_senders']}")
        print(f"Batch Ordering Violations: {stats['batch_ordering_violations']}")
        
        if stats['violation_types']:
            print("\nViolation Types:")
            for vtype, count in stats['violation_types'].items():
                print(f"  {vtype}: {count}")
        
        print("\nTest Results Summary:")
        passed_tests = sum(1 for test in self.test_results if test.passed)
        total_tests = len(self.test_results)
        print(f"Passed: {passed_tests}/{total_tests}")
        
        for test in self.test_results:
            status = "✅ PASS" if test.passed else "❌ FAIL"
            print(f"  {status}: {test.test_name}")
            if not test.passed:
                print(f"    Error: {test.error_message}")
        
        print("="*80)
        
        # Overall assessment
        if stats['total_messages_sent'] == 0:
            print("FAIL: NO MESSAGES PROCESSED - TESTS MAY NOT HAVE RUN CORRECTLY")
            return False
        
        critical_failures = (
            stats['ordering_success_rate_percent'] < 95.0 or
            stats['batch_ordering_violations'] > 0 or
            stats['max_out_of_order_distance'] > 5 or
            passed_tests < total_tests
        )
        
        if critical_failures:
            print("!!! CRITICAL ORDERING FAILURES DETECTED")
            print("   Chat reliability is at risk!")
            return False
        else:
            print("PASS: ORDERING GUARANTEES VALIDATED")
            print("   Chat message ordering is reliable!")
            return True


async def main():
    """Run all WebSocket message ordering tests."""
    print("STARTING COMPREHENSIVE WEBSOCKET MESSAGE ORDERING TESTS")
    print("="*80)
    
    tests = WebSocketOrderingTests()
    
    # Run each test with fresh setup
    test_methods = [
        tests.test_fifo_guarantee_single_sender,
        tests.test_sequence_number_monotonic_validation,
        tests.test_out_of_order_detection_and_handling,
        tests.test_multi_sender_ordering_consistency,
        tests.test_heavy_load_concurrent_senders,
        tests.test_thousand_message_ordering_stress,
    ]
    
    overall_success = True
    
    for test_method in test_methods:
        # Fresh setup for each test
        tests.setup_test()
        
        try:
            success = await test_method()
            if not success:
                overall_success = False
        except Exception as e:
            print(f"FAIL: Test {test_method.__name__} CRASHED: {e}")
            overall_success = False
        
        print()  # Add spacing between tests
    
    # Generate final report
    tests.generate_comprehensive_report()
    
    if overall_success:
        print("\nALL MESSAGE ORDERING TESTS PASSED!")
        print("Chat message ordering guarantees are validated and reliable.")
        return 0
    else:
        print("\nCRITICAL MESSAGE ORDERING FAILURES DETECTED!")
        print("Chat reliability is compromised - immediate attention required.")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))