"""Event Delivery Tracker - Confirmation system for WebSocket events.

This service tracks the delivery of critical WebSocket events and implements
retry logic with exponential backoff for unconfirmed events.

Business Value:
- Ensures reliable delivery of critical tool execution events
- Prevents silent failures that impact user experience
- Provides metrics for event delivery reliability
- Enables automatic retry for transient failures

Architecture:
- Event confirmation tracking with unique IDs
- Timeout and retry logic with exponential backoff
- Delivery metrics collection for monitoring
- Integration with WebSocket bridge and tool dispatcher
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any, Set, List, Callable, Awaitable
from enum import Enum
from dataclasses import dataclass, field
from uuid import uuid4

from netra_backend.app.logging_config import central_logger
from shared.types.core_types import UserID, ThreadID, RunID

logger = central_logger.get_logger(__name__)


class EventDeliveryStatus(Enum):
    """Status of event delivery tracking."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


class EventPriority(Enum):
    """Priority levels for event delivery."""
    CRITICAL = "critical"  # tool_executing, tool_completed
    HIGH = "high"         # agent_started, agent_completed  
    NORMAL = "normal"     # agent_thinking, progress updates
    LOW = "low"          # debug, metrics events


@dataclass
class TrackedEvent:
    """Represents a tracked WebSocket event."""
    event_id: str
    event_type: str
    user_id: UserID
    run_id: RunID
    thread_id: Optional[ThreadID] = None
    priority: EventPriority = EventPriority.NORMAL
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Tracking fields
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: EventDeliveryStatus = EventDeliveryStatus.PENDING
    confirmation_timeout_s: float = 30.0
    max_retries: int = 3
    retry_count: int = 0
    
    # Timing fields
    sent_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    
    # Error tracking
    last_error: Optional[str] = None
    retry_errors: List[str] = field(default_factory=list)
    
    @property
    def is_expired(self) -> bool:
        """Check if event has expired without confirmation."""
        if self.status != EventDeliveryStatus.PENDING:
            return False
        if not self.sent_at:
            return False
        return datetime.now(timezone.utc) > self.sent_at + timedelta(seconds=self.confirmation_timeout_s)
    
    @property
    def can_retry(self) -> bool:
        """Check if event can be retried."""
        return (
            self.status in [EventDeliveryStatus.FAILED, EventDeliveryStatus.TIMEOUT] and
            self.retry_count < self.max_retries
        )
    
    def calculate_retry_delay(self) -> float:
        """Calculate exponential backoff delay for retry."""
        base_delay = 1.0
        max_delay = 30.0
        delay = base_delay * (2 ** self.retry_count)
        return min(delay, max_delay)


@dataclass 
class EventDeliveryMetrics:
    """Metrics for event delivery tracking."""
    total_events_tracked: int = 0
    events_confirmed: int = 0
    events_failed: int = 0
    events_timeout: int = 0
    total_retries: int = 0
    successful_retries: int = 0
    
    # Timing metrics
    average_confirmation_time_ms: float = 0.0
    max_confirmation_time_ms: float = 0.0
    min_confirmation_time_ms: float = float('inf')
    
    # Priority-based metrics
    critical_events_confirmed: int = 0
    critical_events_failed: int = 0
    
    @property
    def confirmation_rate(self) -> float:
        """Calculate confirmation rate percentage."""
        if self.total_events_tracked == 0:
            return 0.0
        return (self.events_confirmed / self.total_events_tracked) * 100.0
    
    @property
    def critical_confirmation_rate(self) -> float:
        """Calculate critical event confirmation rate."""
        total_critical = self.critical_events_confirmed + self.critical_events_failed
        if total_critical == 0:
            return 0.0
        return (self.critical_events_confirmed / total_critical) * 100.0


class EventDeliveryTracker:
    """Service for tracking WebSocket event delivery and implementing retry logic."""
    
    def __init__(self, default_timeout_s: float = 30.0, max_tracked_events: int = 10000):
        """Initialize the event delivery tracker.
        
        Args:
            default_timeout_s: Default timeout for event confirmation
            max_tracked_events: Maximum number of events to track simultaneously
        """
        self.default_timeout_s = default_timeout_s
        self.max_tracked_events = max_tracked_events
        
        # Event tracking storage
        self._tracked_events: Dict[str, TrackedEvent] = {}
        self._user_events: Dict[UserID, Set[str]] = {}  # User -> event_ids
        self._pending_retries: Dict[str, asyncio.Task] = {}
        
        # Retry callback system
        self._retry_callbacks: Dict[str, Callable[[str, str, Dict[str, Any]], Awaitable[bool]]] = {}
        
        # Metrics
        self.metrics = EventDeliveryMetrics()
        
        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_interval_s = 60.0
        self._is_running = False
        
        logger.info("EventDeliveryTracker initialized")
    
    async def start(self):
        """Start the event delivery tracker."""
        if self._is_running:
            return
        
        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("EventDeliveryTracker started")
    
    async def stop(self):
        """Stop the event delivery tracker."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Cancel pending retries
        for task in self._pending_retries.values():
            task.cancel()
        
        # Wait for all retry tasks to complete
        if self._pending_retries:
            await asyncio.gather(*self._pending_retries.values(), return_exceptions=True)
        
        logger.info("EventDeliveryTracker stopped")
    
    def track_event(
        self,
        event_type: str,
        user_id: UserID,
        run_id: RunID,
        thread_id: Optional[ThreadID] = None,
        data: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.NORMAL,
        timeout_s: Optional[float] = None,
        retry_callback: Optional[Callable[[str, str, Dict[str, Any]], Awaitable[bool]]] = None
    ) -> str:
        """Start tracking a WebSocket event.
        
        Args:
            event_type: Type of event (e.g., 'tool_executing', 'tool_completed')
            user_id: User ID for the event
            run_id: Run ID for the event
            thread_id: Optional thread ID
            data: Event data payload
            priority: Event priority level
            timeout_s: Confirmation timeout (uses default if None)
            
        Returns:
            str: Unique event ID for tracking
        """
        # Generate unique event ID
        event_id = f"{event_type}_{user_id}_{run_id}_{int(time.time() * 1000)}_{uuid4().hex[:8]}"
        
        # Create tracked event
        tracked_event = TrackedEvent(
            event_id=event_id,
            event_type=event_type,
            user_id=user_id,
            run_id=run_id,
            thread_id=thread_id,
            priority=priority,
            data=data or {},
            confirmation_timeout_s=timeout_s or self.default_timeout_s
        )
        
        # Store event
        self._tracked_events[event_id] = tracked_event
        
        # Track by user
        if user_id not in self._user_events:
            self._user_events[user_id] = set()
        self._user_events[user_id].add(event_id)
        
        # Store retry callback if provided
        if retry_callback:
            self._retry_callbacks[event_id] = retry_callback
            logger.debug(f"Registered retry callback for event {event_id}")
        
        # Update metrics
        self.metrics.total_events_tracked += 1
        
        # Cleanup old events if we exceed limit
        self._cleanup_if_needed()
        
        logger.debug(f"Tracking event {event_id} ({event_type}) for user {user_id}")
        return event_id
    
    def mark_event_sent(self, event_id: str) -> bool:
        """Mark an event as sent (waiting for confirmation).
        
        Args:
            event_id: Event ID to mark as sent
            
        Returns:
            bool: True if event was found and marked, False otherwise
        """
        tracked_event = self._tracked_events.get(event_id)
        if not tracked_event:
            logger.warning(f"Attempted to mark unknown event as sent: {event_id}")
            return False
        
        tracked_event.sent_at = datetime.now(timezone.utc)
        tracked_event.status = EventDeliveryStatus.PENDING
        
        logger.debug(f"Event {event_id} marked as sent")
        return True
    
    def confirm_event(self, event_id: str) -> bool:
        """Confirm that an event was successfully delivered.
        
        Args:
            event_id: Event ID to confirm
            
        Returns:
            bool: True if event was found and confirmed, False otherwise
        """
        tracked_event = self._tracked_events.get(event_id)
        if not tracked_event:
            logger.warning(f"Attempted to confirm unknown event: {event_id}")
            return False
        
        # Update event status
        tracked_event.status = EventDeliveryStatus.CONFIRMED
        tracked_event.confirmed_at = datetime.now(timezone.utc)
        
        # Update metrics
        self.metrics.events_confirmed += 1
        if tracked_event.priority == EventPriority.CRITICAL:
            self.metrics.critical_events_confirmed += 1
        
        # Calculate confirmation time
        if tracked_event.sent_at:
            confirmation_time_ms = (tracked_event.confirmed_at - tracked_event.sent_at).total_seconds() * 1000
            self._update_timing_metrics(confirmation_time_ms)
        
        logger.debug(f"Event {event_id} confirmed")
        return True
    
    def fail_event(self, event_id: str, error: str) -> bool:
        """Mark an event as failed.
        
        Args:
            event_id: Event ID to mark as failed
            error: Error message
            
        Returns:
            bool: True if event was found and marked, False otherwise
        """
        tracked_event = self._tracked_events.get(event_id)
        if not tracked_event:
            logger.warning(f"Attempted to fail unknown event: {event_id}")
            return False
        
        tracked_event.status = EventDeliveryStatus.FAILED
        tracked_event.failed_at = datetime.now(timezone.utc)
        tracked_event.last_error = error
        
        # Update metrics
        self.metrics.events_failed += 1
        if tracked_event.priority == EventPriority.CRITICAL:
            self.metrics.critical_events_failed += 1
        
        # Schedule retry if eligible and we're running
        if tracked_event.can_retry and self._is_running:
            try:
                self._schedule_retry(event_id)
            except RuntimeError as e:
                if "no running event loop" in str(e):
                    logger.warning(f"Cannot schedule retry for {event_id}: no event loop running")
                else:
                    raise
        
        logger.warning(f"Event {event_id} failed: {error}")
        return True
    
    def get_event_status(self, event_id: str) -> Optional[EventDeliveryStatus]:
        """Get the current status of a tracked event.
        
        Args:
            event_id: Event ID to check
            
        Returns:
            EventDeliveryStatus or None if event not found
        """
        tracked_event = self._tracked_events.get(event_id)
        return tracked_event.status if tracked_event else None
    
    def get_pending_events(self, user_id: Optional[UserID] = None) -> List[TrackedEvent]:
        """Get list of pending events.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of pending TrackedEvent objects
        """
        events = []
        
        if user_id:
            # Get events for specific user
            event_ids = self._user_events.get(user_id, set())
            for event_id in event_ids:
                tracked_event = self._tracked_events.get(event_id)
                if tracked_event and tracked_event.status == EventDeliveryStatus.PENDING:
                    events.append(tracked_event)
        else:
            # Get all pending events
            for tracked_event in self._tracked_events.values():
                if tracked_event.status == EventDeliveryStatus.PENDING:
                    events.append(tracked_event)
        
        return events
    
    def get_expired_events(self) -> List[TrackedEvent]:
        """Get list of events that have expired without confirmation.
        
        Returns:
            List of expired TrackedEvent objects
        """
        expired_events = []
        for tracked_event in self._tracked_events.values():
            if tracked_event.is_expired:
                expired_events.append(tracked_event)
        
        return expired_events
    
    def get_metrics(self) -> EventDeliveryMetrics:
        """Get current delivery metrics.
        
        Returns:
            EventDeliveryMetrics object
        """
        return self.metrics
    
    def _schedule_retry(self, event_id: str):
        """Schedule a retry for a failed event.
        
        Args:
            event_id: Event ID to retry
        """
        tracked_event = self._tracked_events.get(event_id)
        if not tracked_event or not tracked_event.can_retry:
            return
        
        # Cancel existing retry task if any
        if event_id in self._pending_retries:
            self._pending_retries[event_id].cancel()
        
        # Schedule new retry
        retry_delay = tracked_event.calculate_retry_delay()
        self._pending_retries[event_id] = asyncio.create_task(
            self._retry_event_after_delay(event_id, retry_delay)
        )
        
        logger.info(f"Scheduled retry for event {event_id} in {retry_delay:.1f}s (attempt {tracked_event.retry_count + 1})")
    
    async def _retry_event_after_delay(self, event_id: str, delay: float):
        """Retry an event after a delay.
        
        Args:
            event_id: Event ID to retry
            delay: Delay in seconds before retry
        """
        try:
            await asyncio.sleep(delay)
            
            tracked_event = self._tracked_events.get(event_id)
            if not tracked_event or not tracked_event.can_retry:
                return
            
            # Update retry count and status
            tracked_event.retry_count += 1
            tracked_event.status = EventDeliveryStatus.RETRYING
            
            # Update metrics
            self.metrics.total_retries += 1
            
            logger.info(f"Retrying event {event_id} (attempt {tracked_event.retry_count})")
            
            # Execute retry callback if available
            retry_callback = self._retry_callbacks.get(event_id)
            if retry_callback:
                try:
                    success = await retry_callback(event_id, tracked_event.event_type, tracked_event.data)
                    if success:
                        # Reset status to pending and mark as sent
                        tracked_event.status = EventDeliveryStatus.PENDING
                        tracked_event.sent_at = datetime.now(timezone.utc)
                        self.metrics.successful_retries += 1
                        logger.info(f"Successfully retried event {event_id}")
                    else:
                        # Retry failed, will be handled by can_retry check
                        tracked_event.retry_errors.append(f"Retry callback returned False on attempt {tracked_event.retry_count}")
                        logger.warning(f"Retry callback failed for event {event_id}")
                except Exception as callback_error:
                    # Retry callback failed, log and continue
                    error_msg = f"Retry callback error on attempt {tracked_event.retry_count}: {callback_error}"
                    tracked_event.retry_errors.append(error_msg)
                    logger.error(f"Retry callback exception for event {event_id}: {callback_error}")
            else:
                logger.warning(f"No retry callback available for event {event_id} - cannot re-emit")
            
        except asyncio.CancelledError:
            logger.debug(f"Retry cancelled for event {event_id}")
        except Exception as e:
            logger.error(f"Error during retry of event {event_id}: {e}")
        finally:
            # Clean up retry task
            self._pending_retries.pop(event_id, None)
    
    def _update_timing_metrics(self, confirmation_time_ms: float):
        """Update timing metrics with new confirmation time.
        
        Args:
            confirmation_time_ms: Confirmation time in milliseconds
        """
        # Update average (simple moving average)
        if self.metrics.events_confirmed == 1:
            self.metrics.average_confirmation_time_ms = confirmation_time_ms
        else:
            # Weighted average with recent events having more weight
            weight = 0.1  # 10% weight for new value
            self.metrics.average_confirmation_time_ms = (
                (1 - weight) * self.metrics.average_confirmation_time_ms +
                weight * confirmation_time_ms
            )
        
        # Update min/max
        self.metrics.max_confirmation_time_ms = max(
            self.metrics.max_confirmation_time_ms, confirmation_time_ms
        )
        self.metrics.min_confirmation_time_ms = min(
            self.metrics.min_confirmation_time_ms, confirmation_time_ms
        )
    
    def _cleanup_if_needed(self):
        """Clean up old events if we exceed the maximum limit."""
        if len(self._tracked_events) <= self.max_tracked_events:
            return
        
        # Find oldest confirmed/failed events to remove
        events_to_remove = []
        for event_id, tracked_event in self._tracked_events.items():
            if tracked_event.status in [EventDeliveryStatus.CONFIRMED, EventDeliveryStatus.FAILED]:
                events_to_remove.append((event_id, tracked_event.created_at))
        
        # Sort by creation time and remove oldest
        events_to_remove.sort(key=lambda x: x[1])
        num_to_remove = len(self._tracked_events) - self.max_tracked_events + 100  # Remove extra buffer
        
        for event_id, _ in events_to_remove[:num_to_remove]:
            self._remove_event(event_id)
        
        logger.debug(f"Cleaned up {min(num_to_remove, len(events_to_remove))} old events")
    
    def _remove_event(self, event_id: str):
        """Remove an event from tracking.
        
        Args:
            event_id: Event ID to remove
        """
        tracked_event = self._tracked_events.pop(event_id, None)
        if not tracked_event:
            return
        
        # Remove from user tracking
        user_events = self._user_events.get(tracked_event.user_id)
        if user_events:
            user_events.discard(event_id)
            if not user_events:
                del self._user_events[tracked_event.user_id]
        
        # Remove retry callback
        self._retry_callbacks.pop(event_id, None)
        
        # Cancel any pending retry
        retry_task = self._pending_retries.pop(event_id, None)
        if retry_task:
            retry_task.cancel()
    
    async def _cleanup_loop(self):
        """Background loop for cleaning up expired events."""
        while self._is_running:
            try:
                await asyncio.sleep(self._cleanup_interval_s)
                
                # Process expired events
                expired_events = self.get_expired_events()
                for tracked_event in expired_events:
                    tracked_event.status = EventDeliveryStatus.TIMEOUT
                    self.metrics.events_timeout += 1
                    
                    # Schedule retry if eligible
                    if tracked_event.can_retry:
                        try:
                            self._schedule_retry(tracked_event.event_id)
                        except RuntimeError as e:
                            if "no running event loop" in str(e):
                                logger.warning(f"Cannot schedule retry for {tracked_event.event_id}: no event loop running")
                            else:
                                raise
                    
                    logger.warning(f"Event {tracked_event.event_id} timed out after {tracked_event.confirmation_timeout_s}s")
                
                # Periodic cleanup of old events
                self._cleanup_if_needed()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")


# Global instance for easy access
_global_tracker: Optional[EventDeliveryTracker] = None


def get_event_delivery_tracker() -> EventDeliveryTracker:
    """Get the global event delivery tracker instance.
    
    Returns:
        EventDeliveryTracker: Global tracker instance
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = EventDeliveryTracker()
    return _global_tracker


async def initialize_event_delivery_tracker():
    """Initialize and start the global event delivery tracker."""
    tracker = get_event_delivery_tracker()
    await tracker.start()
    logger.info("Global event delivery tracker initialized")


async def shutdown_event_delivery_tracker():
    """Shutdown the global event delivery tracker."""
    global _global_tracker
    if _global_tracker:
        await _global_tracker.stop()
        _global_tracker = None
    logger.info("Global event delivery tracker shutdown")