"""
Event Delivery Tracker - PHASE 2 FIX for Issue #373

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)  
- Business Goal: Reliability & User Experience
- Value Impact: Ensures critical WebSocket events reach users with confirmation tracking
- Strategic Impact: Eliminates silent failures that damage user trust and platform reliability

This component implements comprehensive event delivery tracking and confirmation
for the 5 critical WebSocket events that represent 90% of platform value.

Critical Events Tracked:
1. agent_started - User sees AI is working
2. agent_thinking - Real-time reasoning visibility  
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - Completion signal

Resolves Issue #373 by providing:
- Delivery confirmation tracking
- Retry attempt counting  
- Event delivery status monitoring
- Performance metrics for event reliability
"""

import asyncio
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from collections import defaultdict

from netra_backend.app.logging_config import central_logger
from shared.types.core_types import UserID, ThreadID, RunID

logger = central_logger.get_logger(__name__)


class EventDeliveryStatus(Enum):
    """Event delivery status tracking."""
    PENDING = "pending"           # Event created, not yet sent
    SENT = "sent"                # Event sent to WebSocket 
    CONFIRMED = "confirmed"       # Delivery confirmed by client
    FAILED = "failed"            # Delivery failed permanently
    RETRYING = "retrying"        # Currently retrying delivery
    TIMEOUT = "timeout"          # Delivery timed out


class EventPriority(Enum):
    """Event priority levels for delivery handling."""
    CRITICAL = "critical"        # Must be delivered (agent_started, agent_completed)
    HIGH = "high"               # Important for UX (tool_executing, tool_completed) 
    NORMAL = "normal"           # Nice to have (agent_thinking)
    LOW = "low"                # Background events


@dataclass
class EventDeliveryRecord:
    """Record of event delivery attempt and status."""
    event_id: str
    event_type: str
    user_id: str
    run_id: str
    thread_id: Optional[str]
    priority: EventPriority
    data: Dict[str, Any]
    
    # Delivery tracking
    status: EventDeliveryStatus = EventDeliveryStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    
    # Retry tracking
    attempt_count: int = 0
    max_retries: int = 3
    retry_delay_ms: int = 1000  # Start with 1 second
    timeout_s: float = 30.0
    
    # Error tracking
    last_error: Optional[str] = None
    error_count: int = 0
    
    # Performance metrics
    total_delivery_time_ms: Optional[float] = None
    
    def is_expired(self) -> bool:
        """Check if event has exceeded timeout."""
        if self.status in [EventDeliveryStatus.CONFIRMED, EventDeliveryStatus.FAILED]:
            return False
        
        age_seconds = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age_seconds > self.timeout_s
    
    def should_retry(self) -> bool:
        """Check if event should be retried."""
        return (
            self.status in [EventDeliveryStatus.FAILED, EventDeliveryStatus.TIMEOUT] and
            self.attempt_count < self.max_retries and
            not self.is_expired()
        )
    
    def get_next_retry_delay(self) -> float:
        """Calculate next retry delay with exponential backoff."""
        base_delay = self.retry_delay_ms / 1000.0  # Convert to seconds
        exponential_factor = 2 ** min(self.attempt_count, 5)  # Cap at 32x
        jitter = 0.1 * base_delay  # 10% jitter
        return base_delay * exponential_factor + jitter


class EventDeliveryTracker:
    """
    Tracks WebSocket event delivery attempts, retries, and confirmations.
    
    This is the core component for resolving Issue #373 silent failures.
    Provides comprehensive tracking and retry logic for critical WebSocket events.
    """
    
    def __init__(self):
        """Initialize event delivery tracker."""
        self._events: Dict[str, EventDeliveryRecord] = {}
        self._user_events: Dict[str, List[str]] = defaultdict(list)  # user_id -> event_ids
        self._retry_queue: List[str] = []
        self._cleanup_task: Optional[asyncio.Task] = None
        self._retry_task: Optional[asyncio.Task] = None
        
        # Performance metrics
        self._metrics = {
            'events_tracked': 0,
            'events_confirmed': 0,
            'events_failed': 0,
            'events_retried': 0,
            'average_delivery_time_ms': 0.0,
            'success_rate': 0.0
        }
        
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
        
        logger.info("EventDeliveryTracker initialized for Issue #373 remediation")
    
    def track_event(
        self,
        event_type: str,
        user_id: str, 
        run_id: str,
        thread_id: Optional[str],
        data: Dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        timeout_s: float = 30.0,
        max_retries: int = 3
    ) -> str:
        """
        Track a new event for delivery confirmation.
        
        Args:
            event_type: Type of event (agent_started, tool_executing, etc.)
            user_id: User ID for routing
            run_id: Execution run ID
            thread_id: Optional thread ID
            data: Event data payload
            priority: Event priority level
            timeout_s: Timeout for delivery confirmation
            max_retries: Maximum retry attempts
            
        Returns:
            str: Unique event ID for tracking
        """
        event_id = f"{event_type}_{user_id}_{int(time.time() * 1000)}"
        
        record = EventDeliveryRecord(
            event_id=event_id,
            event_type=event_type,
            user_id=user_id,
            run_id=run_id,
            thread_id=thread_id,
            priority=priority,
            data=data,
            timeout_s=timeout_s,
            max_retries=max_retries
        )
        
        self._events[event_id] = record
        self._user_events[user_id].append(event_id)
        self._metrics['events_tracked'] += 1
        
        logger.debug(
            f"Tracking event {event_id} for user {user_id} "
            f"(type: {event_type}, priority: {priority.value})"
        )
        
        # Start cleanup task if not running
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        return event_id
    
    def mark_event_sent(self, event_id: str) -> bool:
        """
        Mark event as sent to WebSocket.
        
        Args:
            event_id: Event ID to mark as sent
            
        Returns:
            bool: True if event was found and marked
        """
        record = self._events.get(event_id)
        if not record:
            logger.warning(f"Cannot mark unknown event as sent: {event_id}")
            return False
        
        record.status = EventDeliveryStatus.SENT
        record.sent_at = datetime.now(timezone.utc)
        record.attempt_count += 1
        
        logger.debug(f"Event {event_id} marked as sent (attempt {record.attempt_count})")
        return True
    
    def mark_event_confirmed(self, event_id: str) -> bool:
        """
        Mark event as confirmed by client.
        
        Args:
            event_id: Event ID to mark as confirmed
            
        Returns:
            bool: True if event was found and marked
        """
        record = self._events.get(event_id)
        if not record:
            logger.warning(f"Cannot confirm unknown event: {event_id}")
            return False
        
        record.status = EventDeliveryStatus.CONFIRMED
        record.confirmed_at = datetime.now(timezone.utc)
        
        # Calculate delivery time
        if record.sent_at:
            delivery_time_ms = (record.confirmed_at - record.sent_at).total_seconds() * 1000
            record.total_delivery_time_ms = delivery_time_ms
        
        self._metrics['events_confirmed'] += 1
        self._update_success_rate()
        
        logger.debug(f"Event {event_id} confirmed by client")
        return True
    
    def mark_event_failed(self, event_id: str, error: str) -> bool:
        """
        Mark event as failed delivery.
        
        Args:
            event_id: Event ID to mark as failed
            error: Error message describing failure
            
        Returns:
            bool: True if event was found and marked
        """
        record = self._events.get(event_id)
        if not record:
            logger.warning(f"Cannot mark unknown event as failed: {event_id}")
            return False
        
        record.status = EventDeliveryStatus.FAILED  
        record.failed_at = datetime.now(timezone.utc)
        record.last_error = error
        record.error_count += 1
        
        # Add to retry queue if eligible
        if record.should_retry():
            record.status = EventDeliveryStatus.RETRYING
            if event_id not in self._retry_queue:
                self._retry_queue.append(event_id)
                logger.info(
                    f"Event {event_id} added to retry queue "
                    f"(attempt {record.attempt_count}/{record.max_retries})"
                )
        else:
            self._metrics['events_failed'] += 1
            self._update_success_rate()
            logger.error(
                f"Event {event_id} permanently failed after {record.attempt_count} attempts: {error}"
            )
        
        # Start retry task if not running
        if self._retry_queue and (not self._retry_task or self._retry_task.done()):
            self._retry_task = asyncio.create_task(self._process_retry_queue())
        
        return True
    
    def get_event_status(self, event_id: str) -> Optional[EventDeliveryStatus]:
        """Get current status of an event."""
        record = self._events.get(event_id)
        return record.status if record else None
    
    def get_event_record(self, event_id: str) -> Optional[EventDeliveryRecord]:
        """Get complete event record."""
        return self._events.get(event_id)
    
    def get_user_events(self, user_id: str) -> List[EventDeliveryRecord]:
        """Get all events for a specific user."""
        event_ids = self._user_events.get(user_id, [])
        return [self._events[eid] for eid in event_ids if eid in self._events]
    
    def get_pending_events(self) -> List[EventDeliveryRecord]:
        """Get all events pending delivery or confirmation."""
        return [
            record for record in self._events.values()
            if record.status in [
                EventDeliveryStatus.PENDING,
                EventDeliveryStatus.SENT,
                EventDeliveryStatus.RETRYING
            ]
        ]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get delivery tracking metrics."""
        return self._metrics.copy()
    
    async def _process_retry_queue(self) -> None:
        """Process events in retry queue."""
        while self._retry_queue:
            event_id = self._retry_queue.pop(0)
            record = self._events.get(event_id)
            
            if not record or not record.should_retry():
                continue
            
            # Wait for retry delay
            retry_delay = record.get_next_retry_delay()
            await asyncio.sleep(retry_delay)
            
            # Mark as ready for retry
            record.status = EventDeliveryStatus.PENDING
            self._metrics['events_retried'] += 1
            
            logger.info(
                f"Event {event_id} ready for retry "
                f"(attempt {record.attempt_count + 1}/{record.max_retries})"
            )
    
    async def _periodic_cleanup(self) -> None:
        """Periodically clean up old event records."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                
                current_time = datetime.now(timezone.utc)
                cutoff_time = current_time.timestamp() - (24 * 3600)  # 24 hours
                
                # Remove events older than 24 hours
                expired_events = []
                for event_id, record in self._events.items():
                    if record.created_at.timestamp() < cutoff_time:
                        expired_events.append(event_id)
                
                for event_id in expired_events:
                    record = self._events.pop(event_id, None)
                    if record:
                        # Remove from user events
                        user_events = self._user_events.get(record.user_id, [])
                        if event_id in user_events:
                            user_events.remove(event_id)
                        
                        # Remove from retry queue  
                        if event_id in self._retry_queue:
                            self._retry_queue.remove(event_id)
                
                if expired_events:
                    logger.info(f"Cleaned up {len(expired_events)} expired event records")
                
            except Exception as e:
                logger.error(f"Error during periodic cleanup: {e}")
    
    def _update_success_rate(self) -> None:
        """Update success rate metric."""
        total_completed = self._metrics['events_confirmed'] + self._metrics['events_failed']
        if total_completed > 0:
            self._metrics['success_rate'] = self._metrics['events_confirmed'] / total_completed


# Global instance for event tracking
_event_delivery_tracker: Optional[EventDeliveryTracker] = None


def get_event_delivery_tracker() -> EventDeliveryTracker:
    """Get global event delivery tracker instance."""
    global _event_delivery_tracker
    if _event_delivery_tracker is None:
        _event_delivery_tracker = EventDeliveryTracker()
    return _event_delivery_tracker


# Export key classes and functions
__all__ = [
    'EventDeliveryTracker',
    'EventDeliveryStatus', 
    'EventPriority',
    'EventDeliveryRecord',
    'get_event_delivery_tracker'
]