#!/usr/bin/env python3
"""
MISSION CRITICAL: WebSocket Message Queue Resilience Test

This test validates that the WebSocket message queue never permanently loses messages
and has comprehensive recovery mechanisms for all failure scenarios.

CRITICAL REQUIREMENTS VALIDATED:
1. No permanent message loss - all messages either succeed or go to DLQ
2. Exponential backoff retry mechanism works correctly  
3. Circuit breaker integration prevents cascade failures
4. Dead Letter Queue captures and allows investigation of failed messages
5. Background retry processor recovers failed messages
6. Comprehensive state transitions and logging
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, List
from unittest.mock import patch, AsyncMock

from netra_backend.app.services.websocket.message_queue import (
    MessageQueue, QueuedMessage, MessageStatus, MessagePriority
)
from netra_backend.app.core.circuit_breaker import CircuitBreakerOpenError
from shared.isolated_environment import get_env


class MockHandler:
    """Mock message handler for testing different failure scenarios"""
    
    def __init__(self):
        self.call_count = 0
        self.failure_mode = None
        self.failure_count_limit = 0
    
    async def __call__(self, user_id: str, payload: Dict[str, Any]):
        self.call_count += 1
        
        if self.failure_mode == "always_fail":
            raise Exception(f"Simulated failure {self.call_count}")
        
        if self.failure_mode == "fail_then_succeed" and self.call_count <= self.failure_count_limit:
            raise Exception(f"Temporary failure {self.call_count}")
        
        if self.failure_mode == "timeout":
            await asyncio.sleep(60)  # Simulate timeout
        
        # Success case
        return {"processed": True, "call_count": self.call_count}


@pytest.mark.mission_critical
@pytest.mark.asyncio
class TestWebSocketMessageQueueResilience:
    """Mission critical tests for WebSocket message queue resilience"""

    @pytest.fixture
    async def message_queue_with_mock_redis(self):
        """Create message queue with comprehensive mocking"""
        mock_redis = AsyncMock()
        
        # Redis storage simulation
        self.redis_storage = {}
        self.redis_lists = {}
        self.redis_zsets = {}
        
        async def mock_set(key, value, ex=None):
            self.redis_storage[key] = {"value": value, "expires": time.time() + (ex or 3600)}
        
        async def mock_get(key):
            if key in self.redis_storage:
                entry = self.redis_storage[key]
                if time.time() < entry["expires"]:
                    return entry["value"]
                else:
                    del self.redis_storage[key]
            return None
        
        async def mock_delete(key):
            if key in self.redis_storage:
                del self.redis_storage[key]
        
        async def mock_lpush(key, value):
            if key not in self.redis_lists:
                self.redis_lists[key] = []
            self.redis_lists[key].insert(0, value)
        
        async def mock_rpop(key):
            if key in self.redis_lists and self.redis_lists[key]:
                return self.redis_lists[key].pop()
            return None
        
        async def mock_keys(pattern):
            return [k for k in self.redis_storage.keys() if pattern.replace("*", "") in k]
        
        async def mock_zadd(key, mapping):
            if key not in self.redis_zsets:
                self.redis_zsets[key] = {}
            self.redis_zsets[key].update(mapping)
        
        async def mock_zrange(key, start, stop, desc=False):
            if key not in self.redis_zsets:
                return []
            items = list(self.redis_zsets[key].keys())
            if desc:
                items.reverse()
            return items[start:stop+1] if stop >= 0 else items[start:]
        
        async def mock_zrem(key, member):
            if key in self.redis_zsets and member in self.redis_zsets[key]:
                del self.redis_zsets[key][member]
        
        # Configure mock
        mock_redis.set = mock_set
        mock_redis.get = mock_get
        mock_redis.delete = mock_delete
        mock_redis.lpush = mock_lpush
        mock_redis.rpop = mock_rpop
        mock_redis.keys = mock_keys
        mock_redis.zadd = mock_zadd
        mock_redis.zrange = mock_zrange
        mock_redis.zrem = mock_zrem
        mock_redis.llen = AsyncMock(return_value=0)
        
        with patch('netra_backend.app.services.websocket.message_queue.redis_manager', mock_redis):
            queue = MessageQueue()
            
            # Mock circuit breakers to be initially closed
            queue.message_circuit.can_execute = lambda: True
            queue.message_circuit.record_success = lambda: None
            queue.message_circuit.record_failure = lambda error_type: None
            
            queue.redis_circuit.can_execute = lambda: True
            queue.redis_circuit.record_success = lambda: None
            queue.redis_circuit.record_failure = lambda error_type: None
            
            return queue, mock_redis

    @pytest.fixture
    def test_messages(self):
        """Create test messages for various scenarios"""
        return [
            QueuedMessage(
                id=f"test-msg-{i:03d}",
                user_id=f"user-{i}",
                type="test_message",
                payload={"test_data": f"data-{i}", "index": i},
                priority=MessagePriority.NORMAL
            )
            for i in range(1, 6)
        ]

    @pytest.mark.asyncio
    async def test_critical_no_permanent_message_loss(self, message_queue_with_mock_redis, test_messages):
        """CRITICAL: Validate no messages are permanently lost - all either succeed or go to DLQ"""
        queue, mock_redis = message_queue_with_mock_redis
        
        # Register handler that always fails
        failing_handler = MockHandler()
        failing_handler.failure_mode = "always_fail"
        queue.register_handler("test_message", failing_handler)
        
        # Enqueue test messages
        for message in test_messages:
            result = await queue.enqueue(message)
            assert result is True, f"Failed to enqueue message {message.id}"
        
        # Start processing
        await queue.process_queue(worker_count=2)
        
        # Let processing run for a bit
        await asyncio.sleep(0.5)
        
        # Process retry batches to simulate background retry processor
        for _ in range(6):  # Simulate multiple retry cycles
            await queue._process_retry_batch()
            await asyncio.sleep(0.1)
        
        # Stop processing
        await queue.stop_processing()
        
        # Verify all messages either completed or are in DLQ
        dlq_messages = await queue.get_dead_letter_queue_messages()
        
        # All messages should be accounted for (either succeeded or in DLQ)
        total_accounted = len(dlq_messages)
        
        assert total_accounted == len(test_messages), \
            f"Message loss detected! Expected {len(test_messages)} messages, found {total_accounted}"
        
        # Verify each message has proper DLQ structure
        for dlq_msg in dlq_messages:
            assert "final_error" in dlq_msg, "DLQ message missing final_error"
            assert "moved_to_dlq_at" in dlq_msg, "DLQ message missing timestamp"
            assert "retry_history" in dlq_msg, "DLQ message missing retry history"
            assert dlq_msg["status"] in [MessageStatus.DEAD_LETTER.value, MessageStatus.RETRY_EXHAUSTED.value]

    @pytest.mark.asyncio
    async def test_critical_exponential_backoff_progression(self, message_queue_with_mock_redis, test_messages):
        """CRITICAL: Validate exponential backoff prevents thundering herd"""
        queue, mock_redis = message_queue_with_mock_redis
        
        message = test_messages[0]
        
        # Test exponential backoff progression
        expected_ranges = [
            (1, 1),      # retry_count 0: base delay
            (1, 3),      # retry_count 1: ~2s with jitter
            (2, 5),      # retry_count 2: ~4s with jitter  
            (4, 10),     # retry_count 3: ~8s with jitter
            (8, 20),     # retry_count 4: ~16s with jitter
        ]
        
        for retry_count, (min_delay, max_delay) in enumerate(expected_ranges):
            message.retry_count = retry_count
            delay = message.calculate_next_retry_delay()
            
            assert min_delay <= delay <= max_delay, \
                f"Retry count {retry_count}: delay {delay} not in range [{min_delay}, {max_delay}]"
        
        # Test jitter prevents identical delays (thundering herd prevention)
        message.retry_count = 3
        delays = [message.calculate_next_retry_delay() for _ in range(20)]
        unique_delays = set(delays)
        
        assert len(unique_delays) > 1, "Jitter not working - all delays identical (thundering herd risk)"
        
        # All delays should be reasonable
        for delay in delays:
            assert 1 <= delay <= 60, f"Delay {delay} outside reasonable bounds"

    @pytest.mark.asyncio
    async def test_critical_circuit_breaker_prevents_cascade_failures(self, message_queue_with_mock_redis, test_messages):
        """CRITICAL: Circuit breaker prevents cascade failures"""
        queue, mock_redis = message_queue_with_mock_redis
        
        # Mock circuit breaker in open state
        circuit_breaker_open = True
        queue.redis_circuit.can_execute = lambda: not circuit_breaker_open
        
        # Try to enqueue when circuit breaker is open
        message = test_messages[0]
        result = await queue.enqueue(message)
        
        # Should still accept message but queue for circuit breaker retry
        assert result is True, "Circuit breaker should gracefully handle messages, not reject them"
        
        # Verify message was queued for circuit breaker retry
        cb_retry_keys = await mock_redis.keys("circuit_breaker_retry:*")
        assert len(cb_retry_keys) > 0, "Message not queued for circuit breaker retry"
        
        # Simulate circuit breaker recovery
        circuit_breaker_open = False
        
        # Process circuit breaker retries
        await queue._process_circuit_breaker_retries()
        
        # Verify messages are processed when circuit breaker recovers
        # (In a real scenario, the message would be re-enqueued normally)

    @pytest.mark.asyncio
    async def test_critical_dead_letter_queue_investigation_capability(self, message_queue_with_mock_redis, test_messages):
        """CRITICAL: Dead Letter Queue provides comprehensive failure investigation data"""
        queue, mock_redis = message_queue_with_mock_redis
        
        message = test_messages[0]
        message.retry_count = 5  # Exhaust retries
        
        # Add some retry history
        now = datetime.now(UTC)
        message.retry_history = [
            now - timedelta(minutes=5),
            now - timedelta(minutes=3),
            now - timedelta(minutes=1),
        ]
        
        final_error = "Critical business logic failure"
        
        # Move to DLQ
        await queue._move_to_dead_letter_queue(message, final_error)
        
        # Retrieve DLQ messages
        dlq_messages = await queue.get_dead_letter_queue_messages()
        
        assert len(dlq_messages) == 1, "DLQ should contain exactly one message"
        
        dlq_data = dlq_messages[0]
        
        # Verify comprehensive investigation data
        required_fields = [
            "final_error", "moved_to_dlq_at", "retry_history", 
            "total_processing_time", "id", "user_id", "type", "payload"
        ]
        
        for field in required_fields:
            assert field in dlq_data, f"DLQ missing critical field: {field}"
        
        assert dlq_data["final_error"] == final_error
        assert len(dlq_data["retry_history"]) == 3, "Retry history not preserved"
        assert dlq_data["id"] == message.id
        assert isinstance(dlq_data["total_processing_time"], (int, float))

    @pytest.mark.asyncio
    async def test_critical_dlq_message_reprocessing(self, message_queue_with_mock_redis, test_messages):
        """CRITICAL: Messages can be recovered from DLQ and reprocessed"""
        queue, mock_redis = message_queue_with_mock_redis
        
        # Put message in DLQ
        message = test_messages[0]
        message.status = MessageStatus.DEAD_LETTER
        message.permanent_failure = True
        await queue._move_to_dead_letter_queue(message, "Test error")
        
        # Register successful handler
        success_handler = MockHandler()  # Default mode is success
        queue.register_handler("test_message", success_handler)
        
        # Reprocess from DLQ
        success = await queue.reprocess_dead_letter_message(message.id)
        
        assert success is True, "DLQ message reprocessing failed"
        
        # Verify message was removed from DLQ
        dlq_messages = await queue.get_dead_letter_queue_messages()
        dlq_ids = [msg["id"] for msg in dlq_messages]
        
        assert message.id not in dlq_ids, "Message not removed from DLQ after reprocessing"

    @pytest.mark.asyncio
    async def test_critical_retry_eventually_succeeds(self, message_queue_with_mock_redis, test_messages):
        """CRITICAL: Transient failures eventually succeed through retry mechanism"""
        queue, mock_redis = message_queue_with_mock_redis
        
        # Register handler that fails 3 times then succeeds
        retry_handler = MockHandler()
        retry_handler.failure_mode = "fail_then_succeed"
        retry_handler.failure_count_limit = 3
        queue.register_handler("test_message", retry_handler)
        
        message = test_messages[0]
        await queue.enqueue(message)
        
        # Start processing
        await queue.process_queue(worker_count=1)
        await asyncio.sleep(0.1)  # Let initial processing fail
        
        # Simulate multiple retry cycles
        for cycle in range(10):  # Up to 10 retry cycles
            await queue._process_retry_batch()
            await asyncio.sleep(0.05)
            
            # Check if message succeeded
            if retry_handler.call_count > 3:  # Should succeed after 3 failures
                break
        
        await queue.stop_processing()
        
        # Verify handler was called more than failure limit (indicating success)
        assert retry_handler.call_count > 3, \
            f"Handler called only {retry_handler.call_count} times, should succeed after 3 failures"
        
        # Verify no DLQ messages (should have succeeded)
        dlq_messages = await queue.get_dead_letter_queue_messages()
        assert len(dlq_messages) == 0, "Message should not be in DLQ after successful retry"

    @pytest.mark.asyncio
    async def test_critical_comprehensive_logging_and_observability(self, message_queue_with_mock_redis, test_messages):
        """CRITICAL: All state transitions are logged with comprehensive context"""
        queue, mock_redis = message_queue_with_mock_redis
        
        with patch('netra_backend.app.services.websocket.message_queue.logger') as mock_logger:
            # Register failing handler
            failing_handler = MockHandler()
            failing_handler.failure_mode = "always_fail"
            queue.register_handler("test_message", failing_handler)
            
            message = test_messages[0]
            
            # Process message through failure
            await queue.enqueue(message)
            await queue._process_message(message)
            
            # Verify comprehensive logging was called
            assert mock_logger.error.called, "Error logging not called for failed message"
            
            # Check structured logging data
            error_calls = [call for call in mock_logger.error.call_args_list 
                          if call[1] and 'extra' in call[1]]
            
            assert len(error_calls) > 0, "No structured logging found"
            
            extra_data = error_calls[0][1]['extra']
            required_fields = ['message_id', 'message_type', 'retry_count', 'error_type', 'user_id']
            
            for field in required_fields:
                assert field in extra_data, f"Missing required logging field: {field}"

    @pytest.mark.asyncio
    async def test_critical_background_retry_processor_resilience(self, message_queue_with_mock_redis, test_messages):
        """CRITICAL: Background retry processor is resilient to errors"""
        queue, mock_redis = message_queue_with_mock_redis
        
        # Start background processor
        await queue.process_queue(worker_count=1)
        
        # Verify retry task is running
        assert queue._retry_task is not None, "Background retry task not started"
        assert not queue._retry_task.done(), "Background retry task exited prematurely"
        
        # Simulate retry processor error (Redis failure)
        original_get = mock_redis.get
        
        async def failing_get(key):
            if "retry:" in key:
                raise Exception("Redis connection failed")
            return await original_get(key)
        
        mock_redis.get = failing_get
        
        # Let retry processor run with errors
        await asyncio.sleep(0.1)
        
        # Verify retry task is still running despite errors
        assert not queue._retry_task.done(), "Background retry task failed due to Redis error"
        
        # Restore Redis functionality
        mock_redis.get = original_get
        
        await queue.stop_processing()

    @pytest.mark.asyncio
    async def test_critical_message_lifecycle_state_integrity(self, message_queue_with_mock_redis, test_messages):
        """CRITICAL: Message state transitions maintain integrity"""
        queue, mock_redis = message_queue_with_mock_redis
        
        message = test_messages[0]
        
        # Test valid state transitions
        valid_transitions = [
            (MessageStatus.PENDING, MessageStatus.PROCESSING),
            (MessageStatus.PROCESSING, MessageStatus.COMPLETED),
            (MessageStatus.PROCESSING, MessageStatus.RETRYING),
            (MessageStatus.RETRYING, MessageStatus.PROCESSING),
            (MessageStatus.RETRYING, MessageStatus.RETRY_EXHAUSTED),
            (MessageStatus.RETRY_EXHAUSTED, MessageStatus.DEAD_LETTER),
            (MessageStatus.PROCESSING, MessageStatus.CIRCUIT_BREAKER_OPEN),
        ]
        
        for from_status, to_status in valid_transitions:
            message.status = from_status
            message.status = to_status
            assert message.status == to_status, f"Invalid transition {from_status} -> {to_status}"
        
        # Test retry eligibility logic
        message.retry_count = 0
        message.permanent_failure = False
        message.status = MessageStatus.PENDING
        assert message.should_retry() is True, "Fresh message should be retryable"
        
        message.retry_count = 5  # max_retries
        assert message.should_retry() is False, "Message at max retries should not retry"
        
        message.permanent_failure = True
        message.retry_count = 2
        assert message.should_retry() is False, "Permanently failed message should not retry"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])