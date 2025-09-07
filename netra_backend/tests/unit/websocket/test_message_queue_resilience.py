#!/usr/bin/env python3
"""
Comprehensive tests for WebSocket Message Queue Resilience.

Tests the enhanced retry mechanism, circuit breakers, dead letter queue,
and comprehensive failure recovery patterns implemented in the message queue.
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from netra_backend.app.services.websocket.message_queue import (
    MessageQueue, QueuedMessage, MessageStatus, MessagePriority
)
from netra_backend.app.core.circuit_breaker import CircuitBreakerOpenError


class TestMessageQueueResilience:
    """Test suite for message queue resilience features"""

    @pytest.fixture
    async def mock_redis(self):
        """Mock Redis manager for testing"""
        mock = AsyncMock()
        mock.lpush = AsyncMock()
        mock.rpop = AsyncMock()
        mock.set = AsyncMock()
        mock.get = AsyncMock()
        mock.delete = AsyncMock()
        mock.keys = AsyncMock()
        mock.zadd = AsyncMock()
        mock.zrange = AsyncMock()
        mock.zrem = AsyncMock()
        return mock

    @pytest.fixture
    async def message_queue(self, mock_redis):
        """Create message queue with mocked Redis"""
        with patch('netra_backend.app.services.websocket.message_queue.redis_manager', mock_redis):
            queue = MessageQueue()
            # Override redis attribute directly to ensure our mock is used
            queue.redis = mock_redis
            # Mock circuit breakers
            queue.message_circuit = MagicMock()
            queue.message_circuit.can_execute.return_value = True
            queue.message_circuit.record_success = MagicMock()
            queue.message_circuit.record_failure = MagicMock()
            
            queue.redis_circuit = MagicMock()
            queue.redis_circuit.can_execute.return_value = True
            queue.redis_circuit.record_success = MagicMock()
            queue.redis_circuit.record_failure = MagicMock()
            
            # Reset any calls that happened during initialization
            mock_redis.reset_mock()
            return queue

    @pytest.fixture
    def sample_message(self):
        """Create a sample message for testing"""
        return QueuedMessage(
            id="test-msg-001",
            user_id="user-123",
            type="test_message",
            payload={"data": "test"},
            priority=MessagePriority.NORMAL
        )

    @pytest.mark.asyncio
    async def test_exponential_backoff_calculation(self, sample_message):
        """Test exponential backoff delay calculation"""
        message = sample_message
        
        # Test initial retry (should be base delay)
        message.retry_count = 0
        delay = message.calculate_next_retry_delay()
        assert delay == 1  # base_retry_delay
        
        # Test exponential progression (with 0-40% positive jitter)
        message.retry_count = 1
        delay = message.calculate_next_retry_delay()
        assert 1 <= delay <= 2  # 1s + up to 40% jitter
        
        message.retry_count = 2
        delay = message.calculate_next_retry_delay()
        assert 2 <= delay <= 3  # 2s + up to 40% jitter
        
        message.retry_count = 3
        delay = message.calculate_next_retry_delay()
        assert 4 <= delay <= 6  # 4s + up to 40% jitter
        
        message.retry_count = 4
        delay = message.calculate_next_retry_delay()
        assert 8 <= delay <= 12  # 8s + up to 40% jitter
        
        # Test max delay cap
        message.retry_count = 10
        delay = message.calculate_next_retry_delay()
        assert delay <= 60  # Should cap at max_retry_delay

    @pytest.mark.asyncio
    async def test_should_retry_logic(self, sample_message):
        """Test message retry eligibility logic"""
        message = sample_message
        
        # Should retry initially
        assert message.should_retry() is True
        
        # Should retry under max retries
        message.retry_count = 3
        assert message.should_retry() is True
        
        # Should not retry when at max retries
        message.retry_count = 5  # max_retries is 5
        assert message.should_retry() is False
        
        # Should not retry when permanent failure
        message.retry_count = 2
        message.permanent_failure = True
        assert message.should_retry() is False
        
        # Should not retry when completed
        message.permanent_failure = False
        message.status = MessageStatus.COMPLETED
        assert message.should_retry() is False

    @pytest.mark.asyncio
    async def test_retry_ready_timing(self, sample_message):
        """Test retry timing logic"""
        message = sample_message
        
        # Should be ready when no next_retry_at set
        assert message.is_retry_ready() is True
        
        # Should not be ready when future retry time
        message.next_retry_at = datetime.now(UTC) + timedelta(seconds=30)
        assert message.is_retry_ready() is False
        
        # Should be ready when retry time has passed
        message.next_retry_at = datetime.now(UTC) - timedelta(seconds=1)
        assert message.is_retry_ready() is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_protected_enqueue(self, message_queue, mock_redis, sample_message):
        """Test enqueue with circuit breaker protection"""
        # Test normal enqueue when circuit breaker allows
        message_queue.redis_circuit.can_execute.return_value = True
        
        result = await message_queue.enqueue(sample_message)
        
        assert result is True
        mock_redis.lpush.assert_called_once()
        message_queue.redis_circuit.record_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_enqueue(self, message_queue, mock_redis, sample_message):
        """Test enqueue when circuit breaker is open"""
        # Circuit breaker prevents execution
        message_queue.redis_circuit.can_execute.return_value = False
        
        result = await message_queue.enqueue(sample_message)
        
        # Should still return True but queue for circuit breaker retry
        assert result is True
        # Should not call Redis directly
        mock_redis.lpush.assert_not_called()
        # Should store in circuit breaker retry queue
        mock_redis.set.assert_called()

    @pytest.mark.asyncio
    async def test_enhanced_failure_handling(self, message_queue, sample_message):
        """Test enhanced failure handling with comprehensive logging"""
        error_message = "Test error"
        
        # Mock the required methods
        message_queue._update_message_status = AsyncMock()
        message_queue._schedule_retry_with_backoff = AsyncMock()
        message_queue._move_to_dead_letter_queue = AsyncMock()
        message_queue._send_failure_notification = AsyncMock()
        
        # Test retry case
        sample_message.retry_count = 2
        await message_queue._handle_failed_message(sample_message, error_message)
        
        assert sample_message.error == error_message
        assert sample_message.retry_count == 3
        assert sample_message.last_error_type == "Exception"
        assert len(sample_message.retry_history) == 1
        message_queue.message_circuit.record_failure.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_exhausted_moves_to_dlq(self, message_queue, sample_message):
        """Test that retry exhausted messages move to dead letter queue"""
        # Mock required methods
        message_queue._move_to_dead_letter_queue = AsyncMock()
        message_queue._send_failure_notification = AsyncMock()
        
        # Set message to max retries
        sample_message.retry_count = 5  # At max retries
        error_message = "Final error"
        
        await message_queue._handle_retry_exhausted(sample_message, error_message)
        
        assert sample_message.status == MessageStatus.RETRY_EXHAUSTED
        assert sample_message.permanent_failure is True
        message_queue._move_to_dead_letter_queue.assert_called_once_with(sample_message, error_message)
        message_queue._send_failure_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_dead_letter_queue_storage(self, message_queue, mock_redis, sample_message):
        """Test dead letter queue storage functionality"""
        error_message = "Final failure"
        
        # Debug: Check initial state
        initial_set_count = mock_redis.set.call_count
        initial_zadd_count = mock_redis.zadd.call_count
        
        # Test moving message to DLQ
        await message_queue._move_to_dead_letter_queue(sample_message, error_message)
        
        # Verify Redis operations (check delta from initial state)
        # Note: _move_to_dead_letter_queue calls set twice: once for DLQ storage, once for status update
        assert mock_redis.set.call_count - initial_set_count == 2  # Store DLQ message + status update
        assert mock_redis.zadd.call_count - initial_zadd_count == 1  # Add to DLQ index
        
        # Check the stored data structure (get all calls and find the DLQ one)
        set_calls = mock_redis.set.call_args_list
        
        # Find the DLQ call (the one with key starting with "dlq:")
        dlq_call = None
        for call in set_calls:
            if call[0][0].startswith("dlq:"):
                dlq_call = call
                break
        
        assert dlq_call is not None, "DLQ set call not found"
        dlq_key = dlq_call[0][0]
        dlq_data_json = dlq_call[0][1]
        
        assert dlq_key == f"dlq:{sample_message.id}"
        dlq_data = json.loads(dlq_data_json)
        assert dlq_data["final_error"] == error_message
        assert "moved_to_dlq_at" in dlq_data
        assert "total_processing_time" in dlq_data

    @pytest.mark.asyncio
    async def test_background_retry_processor_lifecycle(self, message_queue):
        """Test background retry processor startup and shutdown"""
        # Mock the methods to prevent infinite loops and track calls
        mock_worker = AsyncMock()
        mock_retry_processor = AsyncMock()
        
        with patch.object(message_queue, '_worker', mock_worker):
            with patch.object(message_queue, '_background_retry_processor', mock_retry_processor):
                # Start processing
                await message_queue.process_queue(worker_count=1)
                
                # Verify the retry task was created
                assert message_queue._retry_task is not None
                
                # Stop processing immediately  
                await message_queue.stop_processing()
                
                # Verify cleanup happened
                assert message_queue._running is False
                assert len(message_queue._workers) == 0
                
                # Verify the worker and retry processor were called
                assert mock_worker.called
                assert mock_retry_processor.called

    @pytest.mark.asyncio
    async def test_retry_message_processing(self, message_queue, mock_redis, sample_message):
        """Test processing messages that are ready for retry"""
        # Mock ready retry messages
        sample_message.status = MessageStatus.RETRYING
        sample_message.retry_count = 2
        sample_message.next_retry_at = datetime.now(UTC) - timedelta(seconds=1)  # Ready
        
        message_queue._get_ready_retry_messages = AsyncMock(return_value=[sample_message])
        message_queue._retry_message = AsyncMock()
        
        await message_queue._process_retry_batch()
        
        message_queue._retry_message.assert_called_once_with(sample_message)

    @pytest.mark.asyncio
    async def test_circuit_breaker_retry_processing(self, message_queue, mock_redis, sample_message):
        """Test processing circuit breaker retries when circuit recovers"""
        # Circuit breaker is now closed
        message_queue.redis_circuit.can_execute.return_value = True
        
        # Mock circuit breaker retry message
        mock_redis.keys.return_value = [b"circuit_breaker_retry:test-msg-001"]
        mock_redis.get.return_value = json.dumps(sample_message.to_dict())
        
        # Mock enqueue success
        message_queue.enqueue = AsyncMock(return_value=True)
        
        await message_queue._process_circuit_breaker_retries()
        
        # Should try to enqueue and delete the retry key
        message_queue.enqueue.assert_called_once()
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dlq_messages(self, message_queue, mock_redis):
        """Test retrieving dead letter queue messages"""
        # Mock DLQ index
        mock_redis.zrange.return_value = [b"msg1", b"msg2"]
        
        # Mock DLQ message data
        dlq_data = {"id": "msg1", "status": "dead_letter", "final_error": "Test error"}
        mock_redis.get.return_value = json.dumps(dlq_data)
        
        messages = await message_queue.get_dead_letter_queue_messages(limit=10)
        
        assert len(messages) == 2  # Should have 2 messages
        mock_redis.zrange.assert_called_once_with("dlq_index", 0, 9, desc=True)

    @pytest.mark.asyncio
    async def test_reprocess_dlq_message(self, message_queue, mock_redis, sample_message):
        """Test reprocessing a message from dead letter queue"""
        # Mock DLQ message exists
        dlq_data = sample_message.to_dict()
        dlq_data.update({"status": "dead_letter", "permanent_failure": True})
        mock_redis.get.return_value = json.dumps(dlq_data)
        
        # Mock successful re-enqueue
        message_queue.enqueue = AsyncMock(return_value=True)
        
        success = await message_queue.reprocess_dead_letter_message(sample_message.id)
        
        assert success is True
        # Should delete from DLQ
        mock_redis.delete.assert_called_with(f"dlq:{sample_message.id}")
        mock_redis.zrem.assert_called_with("dlq_index", sample_message.id)
        # Should re-enqueue with reset status
        message_queue.enqueue.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_processing_with_circuit_breaker(self, message_queue, sample_message):
        """Test message processing with circuit breaker protection"""
        # Mock handler and processing steps
        test_handler = AsyncMock()
        message_queue.handlers["test_message"] = test_handler
        
        message_queue._start_message_processing = AsyncMock()
        message_queue._complete_message_processing = AsyncMock()
        message_queue._update_message_status = AsyncMock()
        
        # Test successful processing
        await message_queue._process_message(sample_message)
        
        # Should record success in circuit breaker
        message_queue.message_circuit.record_success.assert_called_once()
        test_handler.assert_called_once_with(sample_message.user_id, sample_message.payload)

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_processing(self, message_queue, sample_message):
        """Test circuit breaker preventing message processing"""
        # Circuit breaker is open
        message_queue.message_circuit.can_execute.return_value = False
        
        message_queue._handle_failed_message = AsyncMock()
        
        await message_queue._process_message(sample_message)
        
        # Should handle as failed due to circuit breaker
        message_queue._handle_failed_message.assert_called_once()
        call_args = message_queue._handle_failed_message.call_args
        assert "circuit breaker" in call_args[0][1].lower()

    @pytest.mark.asyncio
    async def test_comprehensive_error_logging(self, message_queue, sample_message):
        """Test comprehensive error logging with structured data"""
        with patch('netra_backend.app.services.websocket.message_queue.logger') as mock_logger:
            error_message = "Test error with details"
            
            message_queue._update_message_status = AsyncMock()
            message_queue._schedule_retry_with_backoff = AsyncMock()
            
            await message_queue._handle_failed_message(sample_message, error_message)
            
            # Verify error logging was called with structured data
            mock_logger.error.assert_called()
            call_args = mock_logger.error.call_args
            
            # Check that extra data is included
            assert "extra" in call_args[1]
            extra_data = call_args[1]["extra"]
            assert "message_id" in extra_data
            assert "message_type" in extra_data
            assert "retry_count" in extra_data
            assert "error_type" in extra_data

    @pytest.mark.asyncio 
    async def test_retry_jitter_prevents_thundering_herd(self, sample_message):
        """Test that retry delays include jitter to prevent thundering herd"""
        message = sample_message
        message.retry_count = 3
        
        # Calculate multiple delays and ensure they vary
        delays = [message.calculate_next_retry_delay() for _ in range(10)]
        
        # All delays should be different (due to jitter)
        assert len(set(delays)) > 1
        
        # All delays should be within reasonable bounds
        for delay in delays:
            assert 1 <= delay <= 60  # Within base and max limits

    @pytest.mark.asyncio
    async def test_message_status_transitions(self, sample_message):
        """Test proper message status transitions through lifecycle"""
        message = sample_message
        
        # Initial state
        assert message.status == MessageStatus.PENDING
        
        # Processing state
        message.status = MessageStatus.PROCESSING
        assert message.status == MessageStatus.PROCESSING
        
        # Retry state
        message.status = MessageStatus.RETRYING
        assert message.status == MessageStatus.RETRYING
        
        # Circuit breaker state
        message.status = MessageStatus.CIRCUIT_BREAKER_OPEN
        assert message.status == MessageStatus.CIRCUIT_BREAKER_OPEN
        
        # Final states
        message.status = MessageStatus.COMPLETED
        assert message.status == MessageStatus.COMPLETED
        
        message.status = MessageStatus.DEAD_LETTER
        assert message.status == MessageStatus.DEAD_LETTER


@pytest.mark.integration
class TestMessageQueueResilienceIntegration:
    """Integration tests for message queue resilience with real Redis"""

    @pytest.mark.asyncio
    async def test_full_retry_flow_integration(self):
        """Test complete retry flow from failure to recovery"""
        # This would be implemented with real Redis instance
        # and actual message handlers for full integration testing
        pass

    @pytest.mark.asyncio
    async def test_dlq_recovery_integration(self):
        """Test dead letter queue recovery flow integration"""
        # This would test the complete DLQ flow with real storage
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])