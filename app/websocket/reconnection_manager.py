"""Core WebSocket reconnection manager.

Implements individual connection reconnection logic with exponential backoff.
"""

import asyncio
import random
import time
from datetime import datetime, timezone
from typing import Optional, Callable, Any, Dict, List

from app.logging_config import central_logger
from .reconnection_types import (
    ReconnectionState, DisconnectReason, ReconnectionConfig,
    ReconnectionAttempt, ReconnectionMetrics
)

logger = central_logger.get_logger(__name__)


class WebSocketReconnectionManager:
    """Manages WebSocket reconnection with exponential backoff."""
    
    def __init__(self, connection_id: str, config: Optional[ReconnectionConfig] = None):
        self.connection_id = connection_id
        self.config = config or ReconnectionConfig()
        self.state = ReconnectionState.DISCONNECTED
        self.reconnection_task: Optional[asyncio.Task] = None
        self.connect_callback: Optional[Callable] = None
        self.disconnect_callback: Optional[Callable] = None
        self.state_change_callback: Optional[Callable] = None
        self._initialize_tracking_state()

    def _initialize_tracking_state(self) -> None:
        """Initialize reconnection tracking state."""
        self.current_attempt = 0
        self.current_delay_ms = self.config.initial_delay_ms
        self.last_disconnect_time: Optional[datetime] = None
        self.last_successful_connect_time: Optional[datetime] = None
        self.attempt_history: List[ReconnectionAttempt] = []
        self.metrics = ReconnectionMetrics()
        self._stop_reconnecting = False
        self._permanent_failure = False

    async def handle_disconnect(self, reason: DisconnectReason, error_message: Optional[str] = None) -> None:
        """Handle disconnection and start reconnection process."""
        self._record_disconnect(reason)
        if self._is_permanent_failure(reason):
            await self._handle_permanent_failure(reason)
            return
        if not self.config.enabled:
            await self._handle_disabled_reconnection()
            return
        await self._start_reconnection_process()

    def _record_disconnect(self, reason: DisconnectReason) -> None:
        """Record disconnect event and metrics."""
        self.last_disconnect_time = datetime.now(timezone.utc)
        self.metrics.total_disconnects += 1
        self.metrics.last_disconnect_time = self.last_disconnect_time
        reason_key = reason.value
        self.metrics.disconnect_reasons[reason_key] = self.metrics.disconnect_reasons.get(reason_key, 0) + 1
        logger.info(f"Connection {self.connection_id} disconnected: {reason.value}")

    def _is_permanent_failure(self, reason: DisconnectReason) -> bool:
        """Check if disconnect reason indicates permanent failure."""
        return reason.value in self.config.permanent_failure_codes

    async def _handle_permanent_failure(self, reason: DisconnectReason) -> None:
        """Handle permanent failure disconnect."""
        self._permanent_failure = True
        self.state = ReconnectionState.FAILED
        logger.warning(f"Permanent failure for {self.connection_id}: {reason.value}")
        await self._notify_state_change()

    async def _handle_disabled_reconnection(self) -> None:
        """Handle case when reconnection is disabled."""
        self.state = ReconnectionState.DISABLED
        logger.info(f"Reconnection disabled for {self.connection_id}")
        await self._notify_state_change()

    async def _start_reconnection_process(self) -> None:
        """Start the reconnection process."""
        self.state = ReconnectionState.RECONNECTING
        await self._notify_state_change()
        self._cancel_existing_reconnection_task()
        self.reconnection_task = asyncio.create_task(self._reconnection_loop())

    def _cancel_existing_reconnection_task(self) -> None:
        """Cancel existing reconnection task if running."""
        if self.reconnection_task and not self.reconnection_task.done():
            self.reconnection_task.cancel()

    async def handle_successful_connection(self) -> None:
        """Handle successful connection."""
        self._record_successful_connection()
        self._reset_reconnection_state()
        asyncio.create_task(self._schedule_delay_reset())
        logger.info(f"Connection {self.connection_id} successfully established")
        await self._notify_state_change()

    def _record_successful_connection(self) -> None:
        """Record successful connection metrics."""
        self.last_successful_connect_time = datetime.now(timezone.utc)
        self.metrics.last_successful_reconnect_time = self.last_successful_connect_time
        self.state = ReconnectionState.CONNECTED

    def _reset_reconnection_state(self) -> None:
        """Reset reconnection state after successful connection."""
        self.current_attempt = 0
        self._stop_reconnecting = False
        self._permanent_failure = False

    def stop_reconnection(self) -> None:
        """Stop reconnection attempts."""
        self._stop_reconnecting = True
        self._cancel_existing_reconnection_task()
        logger.info(f"Reconnection stopped for {self.connection_id}")

    def set_callbacks(self, connect_callback: Optional[Callable] = None,
                     disconnect_callback: Optional[Callable] = None,
                     state_change_callback: Optional[Callable] = None) -> None:
        """Set callbacks for connection events."""
        self.connect_callback = connect_callback
        self.disconnect_callback = disconnect_callback
        self.state_change_callback = state_change_callback

    async def _reconnection_loop(self) -> None:
        """Main reconnection loop with exponential backoff."""
        while self._should_continue_reconnection():
            attempt = await self._prepare_reconnection_attempt()
            should_continue = await self._execute_backoff_delay(attempt)
            if not should_continue:
                break
            success = await self._attempt_connection(attempt)
            if success:
                return
        await self._finalize_reconnection_loop()

    def _should_continue_reconnection(self) -> bool:
        """Check if reconnection should continue."""
        return (not self._stop_reconnecting and 
                not self._permanent_failure and 
                self.current_attempt < self.config.max_attempts)

    async def _prepare_reconnection_attempt(self) -> ReconnectionAttempt:
        """Prepare next reconnection attempt."""
        self.current_attempt += 1
        self.metrics.total_reconnection_attempts += 1
        delay_ms = self._calculate_backoff_delay()
        attempt = self._create_attempt_record(delay_ms)
        self._log_reconnection_attempt(delay_ms)
        return attempt

    def _create_attempt_record(self, delay_ms: int) -> ReconnectionAttempt:
        """Create reconnection attempt record."""
        return ReconnectionAttempt(
            attempt_number=self.current_attempt,
            timestamp=datetime.now(timezone.utc),
            delay_ms=delay_ms,
            reason=f"Attempt {self.current_attempt}/{self.config.max_attempts}"
        )

    def _log_reconnection_attempt(self, delay_ms: int) -> None:
        """Log reconnection attempt information."""
        logger.info(f"Reconnection attempt {self.current_attempt}/{self.config.max_attempts} "
                   f"for {self.connection_id} in {delay_ms}ms")

    async def _execute_backoff_delay(self, attempt: ReconnectionAttempt) -> bool:
        """Execute backoff delay and check if should continue."""
        try:
            await asyncio.sleep(attempt.delay_ms / 1000.0)
        except asyncio.CancelledError:
            return False
        return not self._stop_reconnecting

    async def _attempt_connection(self, attempt: ReconnectionAttempt) -> bool:
        """Attempt to reconnect and handle result."""
        start_time = time.time()
        await self._set_connecting_state()
        try:
            await self._execute_connection_callback()
            await self._handle_connection_success(attempt, start_time)
            return True
        except Exception as e:
            await self._handle_connection_failure(attempt, start_time, e)
            return False

    async def _set_connecting_state(self) -> None:
        """Set state to connecting and notify."""
        self.state = ReconnectionState.CONNECTING
        await self._notify_state_change()

    async def _execute_connection_callback(self) -> None:
        """Execute connection callback if available."""
        if self.connect_callback:
            await self.connect_callback(self.connection_id)

    async def _handle_connection_success(self, attempt: ReconnectionAttempt, start_time: float) -> None:
        """Handle successful connection attempt."""
        attempt.success = True
        attempt.duration_ms = (time.time() - start_time) * 1000
        self.attempt_history.append(attempt)
        self.metrics.successful_reconnections += 1
        await self.handle_successful_connection()
        self._update_average_reconnection_time(attempt.duration_ms)

    async def _handle_connection_failure(self, attempt: ReconnectionAttempt, start_time: float, error: Exception) -> None:
        """Handle failed connection attempt."""
        attempt.success = False
        attempt.error_message = str(error)
        attempt.duration_ms = (time.time() - start_time) * 1000
        self.attempt_history.append(attempt)
        self.metrics.failed_reconnections += 1
        self._log_connection_failure(error)
        await self._set_reconnecting_state()

    def _log_connection_failure(self, error: Exception) -> None:
        """Log connection failure."""
        logger.warning(f"Reconnection attempt {self.current_attempt} failed for "
                     f"{self.connection_id}: {error}")

    async def _set_reconnecting_state(self) -> None:
        """Set state to reconnecting and notify."""
        self.state = ReconnectionState.RECONNECTING
        await self._notify_state_change()

    async def _finalize_reconnection_loop(self) -> None:
        """Finalize reconnection loop after all attempts."""
        if self.current_attempt >= self.config.max_attempts:
            await self._handle_max_attempts_reached()
        else:
            await self._handle_loop_stopped()

    async def _handle_max_attempts_reached(self) -> None:
        """Handle case when max attempts reached."""
        self.state = ReconnectionState.FAILED
        self._permanent_failure = True
        logger.error(f"Reconnection failed for {self.connection_id} after "
                    f"{self.config.max_attempts} attempts")
        await self._notify_state_change()

    async def _handle_loop_stopped(self) -> None:
        """Handle case when loop stopped before max attempts."""
        self.state = ReconnectionState.DISCONNECTED
        await self._notify_state_change()

    def _calculate_backoff_delay(self) -> int:
        """Calculate exponential backoff delay with jitter."""
        delay = min(
            self.current_delay_ms * (self.config.backoff_multiplier ** (self.current_attempt - 1)),
            self.config.max_delay_ms
        )
        jitter_range = delay * self.config.jitter_factor
        jitter = random.uniform(-jitter_range, jitter_range)
        final_delay = max(0, delay + jitter)
        return int(final_delay)

    async def _schedule_delay_reset(self) -> None:
        """Schedule delay reset after successful connection period."""
        await asyncio.sleep(self.config.reset_delay_after_success_ms / 1000.0)
        if self.state == ReconnectionState.CONNECTED:
            self.current_delay_ms = self.config.initial_delay_ms
            logger.debug(f"Reset reconnection delay for {self.connection_id}")

    def _update_average_reconnection_time(self, duration_ms: float) -> None:
        """Update average reconnection time."""
        successful_count = self.metrics.successful_reconnections
        current_avg = self.metrics.average_reconnection_time_ms
        self.metrics.average_reconnection_time_ms = (
            (current_avg * (successful_count - 1) + duration_ms) / successful_count
        )
        self._update_longest_downtime()

    def _update_longest_downtime(self) -> None:
        """Update longest downtime metric."""
        if self.last_disconnect_time:
            downtime_ms = (datetime.now(timezone.utc) - self.last_disconnect_time).total_seconds() * 1000
            self.metrics.longest_downtime_ms = max(self.metrics.longest_downtime_ms, downtime_ms)

    async def _notify_state_change(self) -> None:
        """Notify about state changes."""
        if self.state_change_callback:
            try:
                if asyncio.iscoroutinefunction(self.state_change_callback):
                    await self.state_change_callback(self.connection_id, self.state)
                else:
                    self.state_change_callback(self.connection_id, self.state)
            except Exception as e:
                logger.error(f"State change callback error for {self.connection_id}: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current reconnection status."""
        return {
            "connection_id": self.connection_id,
            "state": self.state.value,
            "current_attempt": self.current_attempt,
            "max_attempts": self.config.max_attempts,
            "permanent_failure": self._permanent_failure,
            "reconnection_enabled": self.config.enabled,
            "last_disconnect_time": self.last_disconnect_time.isoformat() if self.last_disconnect_time else None,
            "last_successful_connect_time": self.last_successful_connect_time.isoformat() if self.last_successful_connect_time else None,
            "next_attempt_delay_ms": self._calculate_backoff_delay() if self.state == ReconnectionState.RECONNECTING else None
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive reconnection metrics."""
        return {
            "metrics": self.metrics.__dict__,
            "config": self.config.__dict__,
            "recent_attempts": self._format_recent_attempts(),
            "status": self.get_status()
        }

    def _format_recent_attempts(self) -> List[Dict[str, Any]]:
        """Format recent attempts for metrics."""
        return [
            {
                "attempt_number": attempt.attempt_number,
                "timestamp": attempt.timestamp.isoformat(),
                "delay_ms": attempt.delay_ms,
                "success": attempt.success,
                "duration_ms": attempt.duration_ms,
                "error_message": attempt.error_message
            }
            for attempt in self.attempt_history[-10:]  # Last 10 attempts
        ]

    def clear_history(self) -> None:
        """Clear attempt history and reset metrics."""
        self.attempt_history.clear()
        self.metrics = ReconnectionMetrics()
        logger.info(f"Cleared reconnection history for {self.connection_id}")

    def update_config(self, new_config: ReconnectionConfig) -> None:
        """Update reconnection configuration."""
        self.config = new_config
        logger.info(f"Updated reconnection configuration for {self.connection_id}: {new_config}")