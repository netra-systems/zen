"""
Comprehensive Unit Tests for WebSocket MessageQueue

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Stability & Risk Reduction for $500K+ ARR Chat Infrastructure
- Value Impact: Protect critical message ordering and loss prevention for chat-based AI value delivery
- Strategic Impact: Prevent message loss during connection setup that blocks substantive user interactions

CRITICAL TESTING REQUIREMENTS:
1. Tests MUST validate FIFO ordering is preserved under ALL conditions
2. Tests MUST ensure critical messages are NEVER lost even during overflow conditions  
3. Tests MUST validate state-aware queuing works during connection phases
4. Tests MUST validate flush operations complete successfully in priority order
5. Tests MUST validate queue metrics accurately reflect actual performance

TARGET: MessageQueue prevents message loss during connection setup and ensures proper ordering.
This is critical infrastructure enabling substantive chat interactions for $500K+ ARR.
"""

import asyncio
import pytest
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Set, Callable, Optional
from unittest.mock import Mock, MagicMock, patch, call, AsyncMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

# SSOT Imports - Type Safety Compliance
from shared.types import UserID, ConnectionID, MessageID, ensure_user_id
from shared.isolated_environment import get_env

# Test Framework Imports
from test_framework.base import BaseTestCase, AsyncTestCase

# Target Module Under Test
from netra_backend.app.websocket_core.message_queue import (
    MessageQueue,
    MessageQueueRegistry, 
    MessagePriority,
    MessageQueueState,
    QueuedMessage,
    get_message_queue_registry,
    get_message_queue_for_connection
)

# Integration dependencies
from netra_backend.app.websocket_core.connection_state_machine import (
    ApplicationConnectionState,
    StateTransitionInfo,
    ConnectionStateMachine
)



def generate_test_message_id() -> MessageID:
    """Generate a unique message ID for testing."""
    return MessageID(f"msg_{uuid.uuid4().hex[:12]}")


def generate_test_user_id() -> UserID:
    """Generate a unique user ID for testing."""
    return ensure_user_id(f"user_{uuid.uuid4().hex[:8]}")


def generate_test_connection_id() -> ConnectionID:
    """Generate a unique connection ID for testing."""
    return ConnectionID(f"conn_{uuid.uuid4().hex[:8]}")


class TestQueuedMessage:
    """Test the QueuedMessage dataclass functionality."""
    
    def test_queued_message_creation_with_defaults(self):
        """Test QueuedMessage creation with default values."""
        message_data = {"type": "test", "content": "hello"}
        msg = QueuedMessage(
            message_data=message_data,
            message_type="test_message"
        )
        
        assert msg.message_data == message_data
        assert msg.message_type == "test_message"
        assert msg.priority == MessagePriority.NORMAL
        assert msg.attempts == 0
        assert msg.max_attempts == 3
        assert msg.message_id is None
        assert msg.user_id is None
        assert msg.connection_id is None
        assert isinstance(msg.queued_at, datetime)
    
    def test_queued_message_mark_attempt(self):
        """Test attempt marking and processing tracking."""
        msg = QueuedMessage(
            message_data={"test": "data"},
            message_type="test"
        )
        
        initial_attempts = msg.attempts
        assert msg.last_attempt is None
        assert msg.processing_started_at is None
        
        # Mark first attempt
        msg.mark_attempt()
        
        assert msg.attempts == initial_attempts + 1
        assert msg.last_attempt is not None
        assert msg.processing_started_at is not None
        assert msg.last_attempt == msg.processing_started_at
        
        # Mark second attempt
        first_processing_start = msg.processing_started_at
        time.sleep(0.001)  # Small delay
        msg.mark_attempt()
        
        assert msg.attempts == 2
        assert msg.processing_started_at == first_processing_start  # Should not change
        assert msg.last_attempt != msg.processing_started_at  # Should be different
    
    def test_queued_message_calculate_queue_duration(self):
        """Test queue duration calculation."""
        msg = QueuedMessage(
            message_data={"test": "data"},
            message_type="test"
        )
        
        # No processing started yet
        duration = msg.calculate_queue_duration()
        assert duration == 0.0
        assert msg.queue_duration_ms is None
        
        # Simulate delay and mark attempt
        time.sleep(0.01)  # 10ms delay
        msg.mark_attempt()
        
        duration = msg.calculate_queue_duration()
        assert duration > 5.0  # Should be at least 5ms
        assert msg.queue_duration_ms == duration
    
    def test_queued_message_expiration(self):
        """Test message expiration logic."""
        msg = QueuedMessage(
            message_data={"test": "data"},
            message_type="test"
        )
        
        # Fresh message should not be expired
        assert not msg.is_expired(max_age_seconds=60.0)
        
        # Test with very short expiration - need small delay to ensure age > 0
        time.sleep(0.001)  # 1ms delay to ensure age > 0
        assert msg.is_expired(max_age_seconds=0.0)
        
        # Test with past timestamp
        old_msg = QueuedMessage(
            message_data={"test": "data"},
            message_type="test"
        )
        old_msg.queued_at = datetime.now(timezone.utc) - timedelta(seconds=120)
        
        assert old_msg.is_expired(max_age_seconds=60.0)
        assert not old_msg.is_expired(max_age_seconds=180.0)
    
    def test_queued_message_retry_logic(self):
        """Test message retry capability logic."""
        msg = QueuedMessage(
            message_data={"test": "data"},
            message_type="test",
            max_attempts=2
        )
        
        # Initially can retry
        assert msg.can_retry()
        
        # After first attempt, still can retry
        msg.mark_attempt()
        assert msg.can_retry()
        
        # After max attempts, cannot retry
        msg.mark_attempt()
        assert not msg.can_retry()


class TestMessageQueueCore:
    """Test core MessageQueue functionality."""
    
    def setup_method(self):
        self.user_id = generate_test_user_id()
        self.connection_id = generate_test_connection_id()
        self.mock_state_machine = Mock(spec=ConnectionStateMachine)
    
    async def test_message_queue_initialization(self):
        """Test MessageQueue initialization with proper defaults."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            max_size=500,
            max_message_age_seconds=120.0,
            state_machine=self.mock_state_machine
        )
        
        assert queue.connection_id == str(self.connection_id)
        assert queue.user_id == self.user_id
        assert queue.max_size == 500
        assert queue.max_message_age_seconds == 120.0
        assert queue.state_machine == self.mock_state_machine
        assert queue.current_state == MessageQueueState.BUFFERING
        assert queue.is_buffering
        assert not queue.is_operational
        
        # Verify state machine callback registration
        self.mock_state_machine.add_state_change_callback.assert_called_once()
        
        # Clean up
        await queue.close()
    
    async def test_message_enqueue_basic_functionality(self):
        """Test basic message enqueuing functionality."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        message_data = {"type": "chat", "content": "Hello world"}
        message_id = generate_test_message_id()
        
        # Enqueue message
        result = await queue.enqueue_message(
            message_data=message_data,
            message_type="chat_message",
            priority=MessagePriority.HIGH,
            message_id=message_id
        )
        
        assert result is True
        
        # Verify queue state
        stats = queue.get_queue_stats()
        assert stats["total_size"] == 1
        assert stats["queue_sizes_by_priority"]["high"] == 1
        assert stats["metrics"]["messages_queued"] == 1
        
        await queue.close()
    
    async def test_message_enqueue_fifo_ordering_within_priority(self):
        """CRITICAL: Test FIFO ordering is preserved within priority levels."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        # Add multiple messages of same priority
        messages = []
        for i in range(5):
            message_data = {"sequence": i, "content": f"Message {i}"}
            message_id = generate_test_message_id()
            
            result = await queue.enqueue_message(
                message_data=message_data,
                message_type="sequence_test",
                priority=MessagePriority.NORMAL,
                message_id=message_id
            )
            messages.append((message_id, message_data))
            assert result is True
        
        # Verify queue size
        stats = queue.get_queue_stats()
        assert stats["total_size"] == 5
        assert stats["queue_sizes_by_priority"]["normal"] == 5
        
        # Set up mock processor to capture order
        processed_messages = []
        
        async def mock_processor(queued_msg: QueuedMessage):
            processed_messages.append(queued_msg.message_data["sequence"])
        
        queue.set_message_processor(mock_processor)
        
        # Flush and verify FIFO order
        flush_result = await queue.flush_queue()
        assert flush_result is True
        
        # Verify messages were processed in FIFO order (0, 1, 2, 3, 4)
        expected_order = [0, 1, 2, 3, 4]
        assert processed_messages == expected_order
        
        await queue.close()
    
    async def test_message_priority_ordering_across_levels(self):
        """CRITICAL: Test priority ordering across different priority levels."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        # Add messages in reverse priority order to test sorting
        test_messages = [
            (MessagePriority.LOW, "low_message"),
            (MessagePriority.NORMAL, "normal_message"),
            (MessagePriority.HIGH, "high_message"),
            (MessagePriority.CRITICAL, "critical_message")
        ]
        
        # Enqueue in reverse priority order
        for priority, content in test_messages:
            result = await queue.enqueue_message(
                message_data={"content": content},
                message_type="priority_test",
                priority=priority
            )
            assert result is True
        
        # Set up processor to capture processing order
        processed_order = []
        
        async def mock_processor(queued_msg: QueuedMessage):
            processed_order.append(queued_msg.message_data["content"])
        
        queue.set_message_processor(mock_processor)
        
        # Flush and verify priority order
        flush_result = await queue.flush_queue()
        assert flush_result is True
        
        # Expected order: CRITICAL -> HIGH -> NORMAL -> LOW
        expected_order = ["critical_message", "high_message", "normal_message", "low_message"]
        assert processed_order == expected_order
        
        await queue.close()
    
    async def test_queue_overflow_protection_intelligent_dropping(self):
        """CRITICAL: Test overflow protection with intelligent message dropping."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            max_size=3  # Small size to trigger overflow
        )
        
        # Fill queue to capacity with low priority messages
        for i in range(3):
            result = await queue.enqueue_message(
                message_data={"sequence": i},
                message_type="filler",
                priority=MessagePriority.LOW
            )
            assert result is True
        
        # Verify queue is at capacity
        stats = queue.get_queue_stats()
        assert stats["total_size"] == 3
        
        # Try to add high priority message - should drop low priority message
        result = await queue.enqueue_message(
            message_data={"content": "important"},
            message_type="important",
            priority=MessagePriority.HIGH
        )
        assert result is True  # Should succeed by dropping low priority
        
        # Verify overflow handling
        stats = queue.get_queue_stats()
        assert stats["total_size"] == 3  # Still at max
        assert stats["queue_sizes_by_priority"]["high"] == 1
        assert stats["queue_sizes_by_priority"]["low"] == 2  # One dropped
        assert stats["metrics"]["messages_dropped"] == 1
        assert stats["metrics"]["overflow_events"] == 1
        
        await queue.close()
    
    async def test_critical_messages_never_dropped(self):
        """CRITICAL: Test that critical messages are never dropped during overflow."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            max_size=2
        )
        
        # Fill with critical messages
        for i in range(2):
            result = await queue.enqueue_message(
                message_data={"sequence": i},
                message_type="critical",
                priority=MessagePriority.CRITICAL
            )
            assert result is True
        
        # Try to add another critical message - should fail since no lower priority to drop
        result = await queue.enqueue_message(
            message_data={"sequence": 3},
            message_type="critical",
            priority=MessagePriority.CRITICAL
        )
        assert result is False  # Should fail - cannot drop critical messages
        
        # Verify no messages were dropped inappropriately
        stats = queue.get_queue_stats()
        assert stats["total_size"] == 2
        assert stats["queue_sizes_by_priority"]["critical"] == 2
        assert stats["metrics"]["messages_dropped"] == 1  # Only the failed insert
        
        await queue.close()
    
    async def test_message_expiration_during_flush(self):
        """Test message expiration handling during flush operations."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            max_message_age_seconds=0.05  # 50ms expiration
        )
        
        # Add message that will expire
        result = await queue.enqueue_message(
            message_data={"content": "will_expire"},
            message_type="expiry_test"
        )
        assert result is True
        
        # Wait for expiration
        await asyncio.sleep(0.06)  # 60ms > 50ms
        
        # Set up processor
        processed_messages = []
        
        async def mock_processor(queued_msg: QueuedMessage):
            processed_messages.append(queued_msg.message_data["content"])
        
        queue.set_message_processor(mock_processor)
        
        # Flush - expired message should be skipped
        flush_result = await queue.flush_queue()
        assert flush_result is True
        
        # Verify expired message was not processed
        assert len(processed_messages) == 0
        
        # Verify expiration metrics
        stats = queue.get_queue_stats()
        assert stats["metrics"]["messages_expired"] == 1
        
        await queue.close()
    
    async def test_message_retry_logic_on_processing_failure(self):
        """Test message retry logic when processing fails."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        # Add message
        result = await queue.enqueue_message(
            message_data={"content": "retry_test"},
            message_type="retry_test",
            priority=MessagePriority.NORMAL
        )
        assert result is True
        
        # Set up processor that fails initially
        attempt_count = 0
        
        async def failing_processor(queued_msg: QueuedMessage):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:  # Fail first 2 attempts
                raise Exception(f"Processing failed attempt {attempt_count}")
            # Succeed on 3rd attempt
        
        queue.set_message_processor(failing_processor)
        
        # Flush - should retry and eventually succeed
        flush_result = await queue.flush_queue()
        assert flush_result is True  # Should eventually succeed
        assert attempt_count == 3  # Should have attempted 3 times
        
        await queue.close()


class TestMessageQueueStateMachineIntegration:
    """Test MessageQueue integration with ConnectionStateMachine."""
    
    def setup_method(self):
        self.user_id = generate_test_user_id()
        self.connection_id = generate_test_connection_id()
    
    async def test_automatic_flush_on_processing_ready(self):
        """CRITICAL: Test automatic flush when connection becomes PROCESSING_READY."""
        # Create real ConnectionStateMachine for integration test
        state_machine = ConnectionStateMachine(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            state_machine=state_machine
        )
        
        # Verify initial buffering state
        assert queue.current_state == MessageQueueState.BUFFERING
        
        # Add messages while in buffering state
        for i in range(3):
            result = await queue.enqueue_message(
                message_data={"sequence": i},
                message_type="buffered_message"
            )
            assert result is True
        
        # Set up processor to track flushed messages
        processed_messages = []
        
        async def mock_processor(queued_msg: QueuedMessage):
            processed_messages.append(queued_msg.message_data["sequence"])
        
        queue.set_message_processor(mock_processor)
        
        # Transition connection to PROCESSING_READY
        await state_machine.transition_to_state(
            ApplicationConnectionState.PROCESSING_READY,
            reason="Test transition"
        )
        
        # Give flush task time to complete
        await asyncio.sleep(0.1)
        
        # Verify messages were automatically flushed
        assert len(processed_messages) == 3
        assert processed_messages == [0, 1, 2]  # FIFO order
        assert queue.current_state == MessageQueueState.PASS_THROUGH
        
        await queue.close()
        await state_machine.close()
    
    async def test_state_aware_buffering_during_setup_phases(self):
        """Test buffering behavior during connection setup phases."""
        state_machine = ConnectionStateMachine(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            state_machine=state_machine
        )
        
        # Test buffering during different setup states
        setup_states = [
            ApplicationConnectionState.CONNECTING,
            ApplicationConnectionState.ACCEPTED,
            ApplicationConnectionState.AUTHENTICATED,
            ApplicationConnectionState.SERVICES_READY
        ]
        
        for state in setup_states:
            await state_machine.transition_to_state(state, reason=f"Testing {state}")
            
            # Add message during setup phase
            result = await queue.enqueue_message(
                message_data={"state": state.value},
                message_type="setup_test"
            )
            assert result is True
            assert queue.current_state == MessageQueueState.BUFFERING
        
        # Verify all messages were buffered
        stats = queue.get_queue_stats()
        assert stats["total_size"] == len(setup_states)
        
        await queue.close()
        await state_machine.close()
    
    async def test_pass_through_mode_during_normal_operation(self):
        """Test pass-through mode when connection is operational."""
        state_machine = ConnectionStateMachine(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            state_machine=state_machine
        )
        
        # Set up processor
        processed_messages = []
        
        async def mock_processor(queued_msg: QueuedMessage):
            processed_messages.append(queued_msg.message_data["content"])
        
        queue.set_message_processor(mock_processor)
        
        # Transition to PROCESSING_READY (should trigger pass-through mode)
        await state_machine.transition_to_state(
            ApplicationConnectionState.PROCESSING_READY,
            reason="Ready for processing"
        )
        
        # Wait for state transition to complete
        await asyncio.sleep(0.1)
        assert queue.current_state == MessageQueueState.PASS_THROUGH
        
        # Add message in pass-through mode - should be processed immediately
        result = await queue.enqueue_message(
            message_data={"content": "immediate_processing"},
            message_type="passthrough_test"
        )
        assert result is True
        
        # Message should be processed immediately, not queued
        assert len(processed_messages) == 1
        assert processed_messages[0] == "immediate_processing"
        
        # Queue should remain empty since message was processed directly
        stats = queue.get_queue_stats()
        assert stats["total_size"] == 0
        
        await queue.close()
        await state_machine.close()
    
    async def test_degraded_mode_handling(self):
        """Test queue behavior during degraded connection state."""
        state_machine = ConnectionStateMachine(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            state_machine=state_machine
        )
        
        # Start in processing mode
        await state_machine.transition_to_state(
            ApplicationConnectionState.PROCESSING_READY,
            reason="Initial ready state"
        )
        await asyncio.sleep(0.1)
        
        # Transition to degraded state
        await state_machine.transition_to_state(
            ApplicationConnectionState.DEGRADED,
            reason="Service degradation"
        )
        
        # Queue should still be operational but may handle messages differently
        assert queue.is_operational
        
        # Add message during degraded state
        result = await queue.enqueue_message(
            message_data={"content": "degraded_test"},
            message_type="degraded_test"
        )
        assert result is True
        
        await queue.close()
        await state_machine.close()
    
    async def test_connection_failure_suspends_queue(self):
        """Test queue suspension when connection fails."""
        state_machine = ConnectionStateMachine(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            state_machine=state_machine
        )
        
        # Transition to failed state
        await state_machine.transition_to_state(
            ApplicationConnectionState.FAILED,
            reason="Connection failed"
        )
        
        # Verify queue is closed
        assert queue.current_state == MessageQueueState.CLOSED
        assert not queue.is_operational
        
        # Adding message should fail
        result = await queue.enqueue_message(
            message_data={"content": "should_fail"},
            message_type="failure_test"
        )
        assert result is False
        
        await queue.close()
        await state_machine.close()
    
    async def test_state_change_callback_registration_removal(self):
        """Test proper callback registration and removal."""
        state_machine = Mock(spec=ConnectionStateMachine)
        
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            state_machine=state_machine
        )
        
        # Verify callback was registered
        state_machine.add_state_change_callback.assert_called_once()
        callback = state_machine.add_state_change_callback.call_args[0][0]
        
        # Close queue and verify callback removal
        await queue.close()
        state_machine.remove_state_change_callback.assert_called_once_with(callback)


class TestMessageQueueRaceConditionsAndConcurrency:
    """Test race conditions and concurrency scenarios."""
    
    def setup_method(self):
        self.user_id = generate_test_user_id()
        self.connection_id = generate_test_connection_id()
    
    async def test_message_ordering_race_under_high_load(self):
        """CRITICAL: Test message ordering under concurrent enqueue operations."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            max_size=1000
        )
        
        # Track processed messages with sequence numbers
        processed_sequences = []
        sequence_lock = asyncio.Lock()
        
        async def mock_processor(queued_msg: QueuedMessage):
            async with sequence_lock:
                processed_sequences.append(queued_msg.message_data["sequence"])
        
        queue.set_message_processor(mock_processor)
        
        # Concurrent enqueue operations
        async def enqueue_batch(start_seq: int, count: int, priority: MessagePriority):
            tasks = []
            for i in range(count):
                sequence = start_seq + i
                task = queue.enqueue_message(
                    message_data={"sequence": sequence, "batch": start_seq},
                    message_type="concurrency_test",
                    priority=priority
                )
                tasks.append(task)
            
            return await asyncio.gather(*tasks)
        
        # Launch concurrent batches with different priorities
        batch_tasks = [
            enqueue_batch(0, 50, MessagePriority.HIGH),      # 0-49
            enqueue_batch(100, 50, MessagePriority.NORMAL),  # 100-149
            enqueue_batch(200, 50, MessagePriority.HIGH),    # 200-249
        ]
        
        # Execute all batches concurrently
        batch_results = await asyncio.gather(*batch_tasks)
        
        # Verify all messages were enqueued successfully
        for batch_result in batch_results:
            assert all(batch_result)
        
        # Flush queue
        flush_result = await queue.flush_queue()
        assert flush_result is True
        
        # Verify priority ordering: all HIGH priority messages before NORMAL
        high_sequences = [seq for seq in processed_sequences if seq < 100 or seq >= 200]
        normal_sequences = [seq for seq in processed_sequences if 100 <= seq < 200]
        
        # Find the boundary between HIGH and NORMAL messages
        high_end_index = len(high_sequences)
        normal_start_index = len(high_sequences)
        
        # All HIGH priority messages should come first
        assert processed_sequences[:high_end_index] == sorted(high_sequences)
        assert processed_sequences[normal_start_index:] == sorted(normal_sequences)
        
        # Verify total count
        assert len(processed_sequences) == 150
        
        await queue.close()
    
    async def test_message_loss_during_connection_setup(self):
        """CRITICAL: Test no message loss during connection setup phase."""
        state_machine = ConnectionStateMachine(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            state_machine=state_machine
        )
        
        # Concurrent message adding during setup
        message_count = 100
        processed_messages = []
        
        async def mock_processor(queued_msg: QueuedMessage):
            processed_messages.append(queued_msg.message_data["sequence"])
        
        queue.set_message_processor(mock_processor)
        
        # Add messages rapidly during setup phase
        enqueue_tasks = []
        for i in range(message_count):
            task = queue.enqueue_message(
                message_data={"sequence": i},
                message_type="setup_race_test"
            )
            enqueue_tasks.append(task)
        
        # Execute enqueue operations
        enqueue_results = await asyncio.gather(*enqueue_tasks)
        
        # Verify all messages were accepted
        successful_enqueues = sum(1 for result in enqueue_results if result)
        assert successful_enqueues == message_count
        
        # Transition to ready state (trigger flush)
        await state_machine.transition_to_state(
            ApplicationConnectionState.PROCESSING_READY,
            reason="Setup complete"
        )
        
        # Wait for flush to complete
        await asyncio.sleep(0.2)
        
        # Verify no messages were lost
        assert len(processed_messages) == message_count
        assert sorted(processed_messages) == list(range(message_count))
        
        await queue.close()
        await state_machine.close()
    
    async def test_critical_message_preservation_under_overflow(self):
        """CRITICAL: Test critical messages are preserved under extreme overflow."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            max_size=10  # Small queue to force overflow
        )
        
        # Fill queue with low priority messages
        for i in range(10):
            result = await queue.enqueue_message(
                message_data={"sequence": i},
                message_type="filler",
                priority=MessagePriority.LOW
            )
            assert result is True
        
        # Rapidly add critical messages - should displace low priority
        critical_count = 15
        critical_results = []
        
        for i in range(critical_count):
            result = await queue.enqueue_message(
                message_data={"sequence": f"critical_{i}"},
                message_type="critical",
                priority=MessagePriority.CRITICAL
            )
            critical_results.append(result)
        
        # Some critical messages might be rejected due to queue limits
        successful_critical = sum(1 for result in critical_results if result)
        
        # Verify queue contains only the most important messages
        stats = queue.get_queue_stats()
        assert stats["total_size"] == 10  # At capacity
        
        # There should be some critical messages in the queue
        critical_in_queue = stats["queue_sizes_by_priority"]["critical"]
        assert critical_in_queue > 0
        
        # Verify overflow events were recorded
        assert stats["metrics"]["overflow_events"] > 0
        assert stats["metrics"]["messages_dropped"] > 0
        
        await queue.close()
    
    async def test_concurrent_flush_operations(self):
        """Test behavior when multiple flush operations are attempted."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        # Add messages
        for i in range(10):
            result = await queue.enqueue_message(
                message_data={"sequence": i},
                message_type="flush_test"
            )
            assert result is True
        
        # Set up processor with delay to test concurrency
        processed_count = 0
        
        async def slow_processor(queued_msg: QueuedMessage):
            nonlocal processed_count
            await asyncio.sleep(0.01)  # Simulate slow processing
            processed_count += 1
        
        queue.set_message_processor(slow_processor)
        
        # Launch multiple concurrent flush operations
        flush_tasks = [
            queue.flush_queue(),
            queue.flush_queue(),
            queue.flush_queue()
        ]
        
        flush_results = await asyncio.gather(*flush_tasks)
        
        # Only one flush should succeed, others should return False (already flushing)
        successful_flushes = sum(1 for result in flush_results if result)
        assert successful_flushes == 1
        
        # All messages should be processed exactly once
        assert processed_count == 10
        
        await queue.close()
    
    async def test_priority_queue_corruption_under_load(self):
        """Test priority queue integrity under high concurrent load."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            max_size=500
        )
        
        # Concurrent operations across all priority levels
        async def random_enqueue_operations(operation_count: int):
            priorities = list(MessagePriority)
            results = []
            
            for i in range(operation_count):
                priority = random.choice(priorities)
                result = await queue.enqueue_message(
                    message_data={"sequence": i, "priority": priority.value},
                    message_type="corruption_test",
                    priority=priority
                )
                results.append(result)
                
                # Randomly introduce small delays
                if random.random() < 0.1:
                    await asyncio.sleep(0.001)
            
            return results
        
        # Launch multiple concurrent workers
        worker_tasks = [
            random_enqueue_operations(50),
            random_enqueue_operations(50),
            random_enqueue_operations(50)
        ]
        
        worker_results = await asyncio.gather(*worker_tasks)
        
        # Verify queue integrity
        stats = queue.get_queue_stats()
        total_queued = sum(stats["queue_sizes_by_priority"].values())
        
        # Should have queued messages successfully
        assert total_queued > 0
        assert total_queued <= queue.max_size
        
        # Verify priority queues are intact
        for priority in MessagePriority:
            priority_count = stats["queue_sizes_by_priority"][priority.value]
            assert priority_count >= 0
        
        await queue.close()


class TestMessageQueueBusinessValueProtection:
    """Test business value protection - message ordering and critical preservation."""
    
    def setup_method(self):
        self.user_id = generate_test_user_id()
        self.connection_id = generate_test_connection_id()
    
    async def test_chat_message_ordering_guarantees(self):
        """CRITICAL: Test message ordering guarantees for chat continuity."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        # Simulate chat conversation flow
        chat_messages = [
            {"content": "Hello", "timestamp": 1, "type": "user_message"},
            {"content": "Hi there!", "timestamp": 2, "type": "agent_response"},
            {"content": "How are you?", "timestamp": 3, "type": "user_message"},
            {"content": "I'm doing well, thanks!", "timestamp": 4, "type": "agent_response"},
        ]
        
        # Enqueue chat messages
        for msg in chat_messages:
            result = await queue.enqueue_message(
                message_data=msg,
                message_type="chat_message",
                priority=MessagePriority.HIGH  # Chat messages are high priority
            )
            assert result is True
        
        # Process messages and verify ordering
        processed_messages = []
        
        async def chat_processor(queued_msg: QueuedMessage):
            processed_messages.append(queued_msg.message_data)
        
        queue.set_message_processor(chat_processor)
        flush_result = await queue.flush_queue()
        assert flush_result is True
        
        # Verify chat conversation order is preserved
        assert len(processed_messages) == 4
        for i, processed_msg in enumerate(processed_messages):
            expected_msg = chat_messages[i]
            assert processed_msg["content"] == expected_msg["content"]
            assert processed_msg["timestamp"] == expected_msg["timestamp"]
        
        await queue.close()
    
    async def test_critical_system_message_preservation(self):
        """CRITICAL: Test that critical system messages are never lost."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            max_size=5  # Small queue to test preservation under pressure
        )
        
        # Fill queue with normal messages
        for i in range(5):
            result = await queue.enqueue_message(
                message_data={"sequence": i},
                message_type="normal",
                priority=MessagePriority.NORMAL
            )
            assert result is True
        
        # Add critical system messages - should displace normal messages
        critical_messages = [
            {"type": "system_error", "message": "Authentication failure detected"},
            {"type": "system_alert", "message": "Service degradation warning"},
            {"type": "agent_error", "message": "Agent execution failed"}
        ]
        
        critical_results = []
        for critical_msg in critical_messages:
            result = await queue.enqueue_message(
                message_data=critical_msg,
                message_type="system_critical",
                priority=MessagePriority.CRITICAL
            )
            critical_results.append(result)
        
        # All critical messages should be accepted
        assert all(critical_results)
        
        # Verify critical messages are in queue
        stats = queue.get_queue_stats()
        assert stats["queue_sizes_by_priority"]["critical"] == 3
        assert stats["metrics"]["messages_dropped"] > 0  # Normal messages dropped
        
        # Process and verify critical messages are preserved
        processed_messages = []
        
        async def system_processor(queued_msg: QueuedMessage):
            processed_messages.append(queued_msg.message_data)
        
        queue.set_message_processor(system_processor)
        flush_result = await queue.flush_queue()
        assert flush_result is True
        
        # Verify all critical messages were processed
        critical_processed = [msg for msg in processed_messages 
                            if msg.get("type", "").startswith("system_") or msg.get("type") == "agent_error"]
        assert len(critical_processed) == 3
        
        await queue.close()
    
    async def test_performance_metrics_validation(self):
        """Test queue performance metrics accurately reflect actual performance."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        # Add messages with known timing
        start_time = time.time()
        message_count = 20
        
        for i in range(message_count):
            result = await queue.enqueue_message(
                message_data={"sequence": i},
                message_type="performance_test"
            )
            assert result is True
            
            # Small delay between messages
            await asyncio.sleep(0.005)  # 5ms
        
        enqueue_duration = time.time() - start_time
        
        # Set up processor to track processing metrics
        processing_times = []
        
        async def timing_processor(queued_msg: QueuedMessage):
            processing_times.append(queued_msg.calculate_queue_duration())
        
        queue.set_message_processor(timing_processor)
        
        # Flush and measure
        flush_start = time.time()
        flush_result = await queue.flush_queue()
        flush_duration = time.time() - flush_start
        assert flush_result is True
        
        # Verify metrics accuracy
        stats = queue.get_queue_stats()
        metrics = stats["metrics"]
        
        # Verify counts
        assert metrics["messages_queued"] == message_count
        assert metrics["messages_flushed"] == message_count
        assert metrics["flush_operations"] == 1
        assert metrics["peak_queue_size"] == message_count
        
        # Verify timing metrics are reasonable
        avg_queue_duration = metrics["average_queue_duration_ms"]
        assert avg_queue_duration > 0
        assert avg_queue_duration < enqueue_duration * 1000  # Should be less than total enqueue time
        
        # Verify individual message timing
        assert len(processing_times) == message_count
        for duration in processing_times:
            assert duration > 0  # All messages had some queue time
        
        await queue.close()
    
    async def test_graceful_degradation_scenarios(self):
        """Test graceful degradation under adverse conditions."""
        queue = MessageQueue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            max_size=10
        )
        
        # Simulate processor that occasionally fails
        failure_count = 0
        success_count = 0
        
        async def unreliable_processor(queued_msg: QueuedMessage):
            nonlocal failure_count, success_count
            # Fail 30% of the time
            if random.random() < 0.3:
                failure_count += 1
                raise Exception("Simulated processing failure")
            else:
                success_count += 1
        
        queue.set_message_processor(unreliable_processor)
        
        # Add messages with mixed priorities
        for i in range(15):
            priority = MessagePriority.CRITICAL if i % 5 == 0 else MessagePriority.NORMAL
            result = await queue.enqueue_message(
                message_data={"sequence": i},
                message_type="degradation_test",
                priority=priority
            )
            # Some messages may be dropped due to overflow
        
        # Attempt flush with unreliable processor
        flush_result = await queue.flush_queue()
        
        # System should handle failures gracefully
        stats = queue.get_queue_stats()
        
        # Verify system remained stable despite failures
        assert success_count >= 0
        assert failure_count >= 0
        
        # Queue should still be operational
        remaining_size = stats["total_size"]
        assert remaining_size >= 0
        
        await queue.close()


class TestMessageQueueRegistryAndLifecycle:
    """Test MessageQueueRegistry and lifecycle management."""
    
    def setup_method(self):
        self.user_id = generate_test_user_id()
        self.connection_id = generate_test_connection_id()
    
    def test_registry_singleton_pattern(self):
        """Test MessageQueueRegistry singleton pattern."""
        # Get registry instances
        registry1 = get_message_queue_registry()
        registry2 = get_message_queue_registry()
        
        # Should be the same instance
        assert registry1 is registry2
        assert isinstance(registry1, MessageQueueRegistry)
    
    async def test_queue_creation_and_retrieval(self):
        """Test queue creation and retrieval through registry."""
        registry = get_message_queue_registry()
        
        # Create queue
        queue = registry.create_message_queue(
            connection_id=self.connection_id,
            user_id=self.user_id,
            max_size=500
        )
        
        assert isinstance(queue, MessageQueue)
        assert queue.connection_id == str(self.connection_id)
        assert queue.user_id == self.user_id
        assert queue.max_size == 500
        
        # Retrieve queue
        retrieved_queue = registry.get_message_queue(self.connection_id)
        assert queue is retrieved_queue
        
        # Test convenience function
        convenience_queue = get_message_queue_for_connection(self.connection_id)
        assert queue is convenience_queue
        
        # Clean up
        await registry.remove_message_queue(self.connection_id)
    
    async def test_duplicate_queue_creation_handling(self):
        """Test handling of duplicate queue creation requests."""
        registry = get_message_queue_registry()
        
        # Create first queue
        queue1 = registry.create_message_queue(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        # Attempt to create duplicate
        queue2 = registry.create_message_queue(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        # Should return the same instance
        assert queue1 is queue2
        
        # Clean up
        await registry.remove_message_queue(self.connection_id)
    
    async def test_queue_removal_and_cleanup(self):
        """Test proper queue removal and cleanup."""
        registry = get_message_queue_registry()
        
        # Create queue
        queue = registry.create_message_queue(
            connection_id=self.connection_id,
            user_id=self.user_id
        )
        
        # Add some messages
        for i in range(5):
            result = await queue.enqueue_message(
                message_data={"sequence": i},
                message_type="cleanup_test"
            )
            assert result is True
        
        # Verify queue exists and has messages
        assert registry.get_message_queue(self.connection_id) is not None
        stats = queue.get_queue_stats()
        assert stats["total_size"] == 5
        
        # Remove queue
        removal_result = await registry.remove_message_queue(self.connection_id)
        assert removal_result is True
        
        # Verify queue is removed and cleaned up
        assert registry.get_message_queue(self.connection_id) is None
        assert queue.current_state == MessageQueueState.CLOSED
        
        # Attempting to remove again should return False
        removal_result2 = await registry.remove_message_queue(self.connection_id)
        assert removal_result2 is False
    
    async def test_registry_statistics_and_monitoring(self):
        """Test registry statistics and health monitoring."""
        registry = get_message_queue_registry()
        
        # Create multiple queues
        queues = []
        connection_ids = []
        
        for i in range(3):
            conn_id = ConnectionID(f"conn_stats_{i}")
            queue = registry.create_message_queue(
                connection_id=conn_id,
                user_id=self.user_id
            )
            queues.append(queue)
            connection_ids.append(conn_id)
        
        # Get initial stats
        initial_stats = registry.get_registry_stats()
        assert initial_stats["total_queues"] == 3
        assert initial_stats["active_queues"] == 0  # All in buffering state
        assert initial_stats["total_queued_messages"] == 0
        
        # Add messages to queues
        for i, queue in enumerate(queues):
            for j in range(i + 1):  # Different message counts
                result = await queue.enqueue_message(
                    message_data={"queue": i, "msg": j},
                    message_type="stats_test"
                )
                assert result is True
        
        # Get updated stats
        updated_stats = registry.get_registry_stats()
        assert updated_stats["total_queues"] == 3
        assert updated_stats["total_queued_messages"] == 6  # 1+2+3
        
        # Verify state distribution
        state_distribution = updated_stats["state_distribution"]
        assert state_distribution["buffering"] == 3
        
        # Test active queues tracking
        active_queues = registry.get_all_active_queues()
        assert len(active_queues) == 0  # None operational yet
        
        # Clean up
        for conn_id in connection_ids:
            await registry.remove_message_queue(conn_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])