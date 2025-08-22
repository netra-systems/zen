"""Transactional Batch Message Processing.

Handles transactional message processing with state management and retry logic.
Implements the mandatory pattern from websocket_reliability.xml.
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple

from netra_backend.app.websocket.batch_message_types import (
    BatchConfig,
    MessageState,
    PendingMessage,
)
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TransactionalBatchProcessor:
    """Handles transactional message processing with guaranteed delivery."""
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self._retry_delays = [0.1, 0.5, 2.0, 8.0]  # Exponential backoff
    
    def mark_batch_sending(self, messages: List[PendingMessage]) -> List[PendingMessage]:
        """Mark batch messages as SENDING (transactional step 1)."""
        sending_batch = []
        for msg in messages:
            sending_batch.append(self._mark_message_sending(msg))
        return sending_batch
    
    def _mark_message_sending(self, msg: PendingMessage) -> PendingMessage:
        """Mark single message as SENDING."""
        if msg.state == MessageState.PENDING:
            msg.state = MessageState.SENDING
        return msg
    
    def mark_batch_sent(self, messages: List[PendingMessage]) -> None:
        """Mark batch messages as SENT after confirmation."""
        for msg in messages:
            self._mark_message_sent(msg)
    
    def _mark_message_sent(self, msg: PendingMessage) -> None:
        """Mark single message as SENT."""
        msg.state = MessageState.SENT
    
    def mark_batch_failed(self, messages: List[PendingMessage]) -> None:
        """Mark batch messages as FAILED on send failure."""
        for msg in messages:
            self._mark_message_failed(msg)
    
    def _mark_message_failed(self, msg: PendingMessage) -> None:
        """Mark single message as FAILED with retry info."""
        msg.state = MessageState.FAILED
        msg.retry_count += 1
        msg.last_retry_time = time.time()
    
    def revert_batch_to_pending(self, messages: List[PendingMessage]) -> None:
        """Revert batch messages to PENDING state."""
        for msg in messages:
            self._revert_message_to_pending(msg)
    
    def _revert_message_to_pending(self, msg: PendingMessage) -> None:
        """Revert single message to PENDING state."""
        if msg.state == MessageState.SENDING:
            msg.state = MessageState.PENDING


class RetryManager:
    """Manages message retry logic with exponential backoff."""
    
    def __init__(self):
        self._base_delay = 0.1
        self._max_delay = 30.0
        self._backoff_factor = 2.0
    
    def should_retry(self, msg: PendingMessage) -> bool:
        """Determine if message should be retried."""
        return self._check_retry_eligibility(msg)
    
    def _check_retry_eligibility(self, msg: PendingMessage) -> bool:
        """Check if message is eligible for retry."""
        within_retry_limit = msg.retry_count < msg.max_retries
        enough_time_passed = self._has_enough_time_passed(msg)
        return within_retry_limit and enough_time_passed
    
    def _has_enough_time_passed(self, msg: PendingMessage) -> bool:
        """Check if enough time has passed for retry."""
        if msg.last_retry_time == 0:
            return True
        retry_delay = self._calculate_retry_delay(msg.retry_count)
        return time.time() - msg.last_retry_time >= retry_delay
    
    def _calculate_retry_delay(self, retry_count: int) -> float:
        """Calculate exponential backoff delay."""
        delay = self._base_delay * (self._backoff_factor ** retry_count)
        return min(delay, self._max_delay)
    
    def get_next_retry_time(self, msg: PendingMessage) -> float:
        """Get the next retry time for a message."""
        retry_delay = self._calculate_retry_delay(msg.retry_count)
        return msg.last_retry_time + retry_delay
    
    def filter_retryable_messages(self, messages: List[PendingMessage]) -> List[PendingMessage]:
        """Filter messages that are eligible for retry."""
        return [msg for msg in messages if self.should_retry(msg)]


class MessageStateManager:
    """Manages message state transitions and cleanup."""
    
    def get_pending_messages(self, messages: List[PendingMessage]) -> List[PendingMessage]:
        """Get messages in PENDING state."""
        return [msg for msg in messages if msg.state == MessageState.PENDING]
    
    def get_sent_messages(self, messages: List[PendingMessage]) -> List[PendingMessage]:
        """Get messages in SENT state."""
        return [msg for msg in messages if msg.state == MessageState.SENT]
    
    def get_failed_messages(self, messages: List[PendingMessage]) -> List[PendingMessage]:
        """Get messages in FAILED state."""
        return [msg for msg in messages if msg.state == MessageState.FAILED]
    
    def remove_sent_messages(self, message_queue: List[PendingMessage]) -> List[PendingMessage]:
        """Remove SENT messages from queue, keeping others."""
        return [msg for msg in message_queue if msg.state != MessageState.SENT]
    
    def count_by_state(self, messages: List[PendingMessage]) -> Dict[MessageState, int]:
        """Count messages by state."""
        counts = {state: 0 for state in MessageState}
        for msg in messages:
            counts[msg.state] += 1
        return counts