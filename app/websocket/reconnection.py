"""WebSocket Reconnection System with Exponential Backoff.

Implements robust reconnection logic for WebSocket connections
with exponential backoff, jitter, and intelligent retry strategies.
"""

import asyncio
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Callable, Any, List
from dataclasses import dataclass, field
from enum import Enum

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ReconnectionState(str, Enum):
    """Reconnection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    DISABLED = "disabled"


class DisconnectReason(str, Enum):
    """Disconnect reason codes."""
    NORMAL_CLOSURE = "normal_closure"
    CONNECTION_ERROR = "connection_error"
    HEARTBEAT_TIMEOUT = "heartbeat_timeout"
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMITED = "rate_limited"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


@dataclass
class ReconnectionConfig:
    """Reconnection configuration."""
    enabled: bool = True
    initial_delay_ms: int = 1000  # 1 second
    max_delay_ms: int = 30000     # 30 seconds
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1    # 10% jitter
    max_attempts: int = 10
    reset_delay_after_success_ms: int = 300000  # 5 minutes
    permanent_failure_codes: List[str] = field(default_factory=lambda: [
        DisconnectReason.AUTHENTICATION_FAILED.value,
        DisconnectReason.RATE_LIMITED.value
    ])


@dataclass
class ReconnectionAttempt:
    """Single reconnection attempt record."""
    attempt_number: int
    timestamp: datetime
    delay_ms: int
    reason: str
    success: bool = False
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None


@dataclass
class ReconnectionMetrics:
    """Reconnection metrics and statistics."""
    total_disconnects: int = 0
    total_reconnection_attempts: int = 0
    successful_reconnections: int = 0
    failed_reconnections: int = 0
    average_reconnection_time_ms: float = 0.0
    longest_downtime_ms: float = 0.0
    disconnect_reasons: Dict[str, int] = field(default_factory=dict)
    last_disconnect_time: Optional[datetime] = None
    last_successful_reconnect_time: Optional[datetime] = None


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
        
        # Tracking variables
        self.current_attempt = 0
        self.current_delay_ms = self.config.initial_delay_ms
        self.last_disconnect_time: Optional[datetime] = None
        self.last_successful_connect_time: Optional[datetime] = None
        self.attempt_history: List[ReconnectionAttempt] = []
        self.metrics = ReconnectionMetrics()
        
        # Stop conditions
        self._stop_reconnecting = False
        self._permanent_failure = False
    
    async def handle_disconnect(self, reason: DisconnectReason, error_message: Optional[str] = None) -> None:
        """Handle disconnection and start reconnection process."""
        self.last_disconnect_time = datetime.now(timezone.utc)
        self.metrics.total_disconnects += 1
        self.metrics.last_disconnect_time = self.last_disconnect_time
        
        # Track disconnect reason
        reason_key = reason.value
        self.metrics.disconnect_reasons[reason_key] = self.metrics.disconnect_reasons.get(reason_key, 0) + 1
        
        logger.info(f"Connection {self.connection_id} disconnected: {reason.value} - {error_message}")
        
        # Check if this is a permanent failure
        if reason.value in self.config.permanent_failure_codes:
            self._permanent_failure = True
            self.state = ReconnectionState.FAILED
            logger.warning(f"Permanent failure for {self.connection_id}: {reason.value}")
            await self._notify_state_change()
            return
        
        # Check if reconnection is enabled
        if not self.config.enabled:
            self.state = ReconnectionState.DISABLED
            logger.info(f"Reconnection disabled for {self.connection_id}")
            await self._notify_state_change()
            return
        
        # Start reconnection process
        self.state = ReconnectionState.RECONNECTING
        await self._notify_state_change()
        
        if self.reconnection_task and not self.reconnection_task.done():
            self.reconnection_task.cancel()
        
        self.reconnection_task = asyncio.create_task(self._reconnection_loop())
    
    async def handle_successful_connection(self) -> None:
        """Handle successful connection."""
        self.last_successful_connect_time = datetime.now(timezone.utc)
        self.metrics.last_successful_reconnect_time = self.last_successful_connect_time
        self.state = ReconnectionState.CONNECTED
        
        # Reset reconnection state
        self.current_attempt = 0
        self._stop_reconnecting = False
        self._permanent_failure = False
        
        # Schedule delay reset (after successful connection period)
        asyncio.create_task(self._schedule_delay_reset())
        
        logger.info(f"Connection {self.connection_id} successfully established")
        await self._notify_state_change()
    
    def stop_reconnection(self) -> None:
        """Stop reconnection attempts."""
        self._stop_reconnecting = True
        if self.reconnection_task and not self.reconnection_task.done():
            self.reconnection_task.cancel()
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
        while (not self._stop_reconnecting and 
               not self._permanent_failure and 
               self.current_attempt < self.config.max_attempts):
            
            self.current_attempt += 1
            self.metrics.total_reconnection_attempts += 1
            
            # Calculate delay with exponential backoff and jitter
            delay_ms = self._calculate_backoff_delay()
            
            # Record attempt
            attempt = ReconnectionAttempt(
                attempt_number=self.current_attempt,
                timestamp=datetime.now(timezone.utc),
                delay_ms=delay_ms,
                reason=f"Attempt {self.current_attempt}/{self.config.max_attempts}"
            )
            
            logger.info(f"Reconnection attempt {self.current_attempt}/{self.config.max_attempts} "
                       f"for {self.connection_id} in {delay_ms}ms")
            
            # Wait for backoff delay
            try:
                await asyncio.sleep(delay_ms / 1000.0)
            except asyncio.CancelledError:
                break
            
            if self._stop_reconnecting:
                break
            
            # Attempt to reconnect
            start_time = time.time()
            self.state = ReconnectionState.CONNECTING
            await self._notify_state_change()
            
            try:
                if self.connect_callback:
                    await self.connect_callback(self.connection_id)
                
                # Connection successful
                attempt.success = True
                attempt.duration_ms = (time.time() - start_time) * 1000
                self.attempt_history.append(attempt)
                
                self.metrics.successful_reconnections += 1
                await self.handle_successful_connection()
                
                # Update average reconnection time
                self._update_average_reconnection_time(attempt.duration_ms)
                
                return  # Exit loop on success
                
            except Exception as e:
                # Connection failed
                attempt.success = False
                attempt.error_message = str(e)
                attempt.duration_ms = (time.time() - start_time) * 1000
                self.attempt_history.append(attempt)
                
                self.metrics.failed_reconnections += 1
                
                logger.warning(f"Reconnection attempt {self.current_attempt} failed for "
                             f"{self.connection_id}: {e}")
                
                self.state = ReconnectionState.RECONNECTING
                await self._notify_state_change()
        
        # All attempts exhausted or stopped
        if self.current_attempt >= self.config.max_attempts:
            self.state = ReconnectionState.FAILED
            self._permanent_failure = True
            logger.error(f"Reconnection failed for {self.connection_id} after "
                        f"{self.config.max_attempts} attempts")
        else:
            self.state = ReconnectionState.DISCONNECTED
        
        await self._notify_state_change()
    
    def _calculate_backoff_delay(self) -> int:
        """Calculate exponential backoff delay with jitter."""
        # Exponential backoff
        delay = min(
            self.current_delay_ms * (self.config.backoff_multiplier ** (self.current_attempt - 1)),
            self.config.max_delay_ms
        )
        
        # Add jitter to avoid thundering herd
        jitter_range = delay * self.config.jitter_factor
        jitter = random.uniform(-jitter_range, jitter_range)
        
        final_delay = max(0, delay + jitter)
        return int(final_delay)
    
    async def _schedule_delay_reset(self) -> None:
        """Schedule delay reset after successful connection period."""
        await asyncio.sleep(self.config.reset_delay_after_success_ms / 1000.0)
        
        # Reset delay if connection is still active
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
        
        # Update longest downtime
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
            "recent_attempts": [
                {
                    "attempt_number": attempt.attempt_number,
                    "timestamp": attempt.timestamp.isoformat(),
                    "delay_ms": attempt.delay_ms,
                    "success": attempt.success,
                    "duration_ms": attempt.duration_ms,
                    "error_message": attempt.error_message
                }
                for attempt in self.attempt_history[-10:]  # Last 10 attempts
            ],
            "status": self.get_status()
        }
    
    def clear_history(self) -> None:
        """Clear attempt history and reset metrics."""
        self.attempt_history.clear()
        self.metrics = ReconnectionMetrics()
        logger.info(f"Cleared reconnection history for {self.connection_id}")
    
    def update_config(self, new_config: ReconnectionConfig) -> None:
        """Update reconnection configuration."""
        self.config = new_config
        logger.info(f"Updated reconnection configuration for {self.connection_id}: {new_config}")


class GlobalReconnectionManager:
    """Manages reconnection for multiple WebSocket connections."""
    
    def __init__(self, default_config: Optional[ReconnectionConfig] = None):
        self.default_config = default_config or ReconnectionConfig()
        self.connection_managers: Dict[str, WebSocketReconnectionManager] = {}
    
    def get_or_create_manager(self, connection_id: str, 
                             config: Optional[ReconnectionConfig] = None) -> WebSocketReconnectionManager:
        """Get existing or create new reconnection manager."""
        if connection_id not in self.connection_managers:
            self.connection_managers[connection_id] = WebSocketReconnectionManager(
                connection_id, config or self.default_config
            )
        return self.connection_managers[connection_id]
    
    def remove_manager(self, connection_id: str) -> None:
        """Remove reconnection manager for a connection."""
        if connection_id in self.connection_managers:
            manager = self.connection_managers[connection_id]
            manager.stop_reconnection()
            del self.connection_managers[connection_id]
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global reconnection statistics."""
        total_connections = len(self.connection_managers)
        active_reconnections = sum(1 for mgr in self.connection_managers.values() 
                                 if mgr.state == ReconnectionState.RECONNECTING)
        failed_connections = sum(1 for mgr in self.connection_managers.values() 
                               if mgr.state == ReconnectionState.FAILED)
        
        return {
            "total_managed_connections": total_connections,
            "active_reconnections": active_reconnections,
            "failed_connections": failed_connections,
            "managers": {
                conn_id: manager.get_status() 
                for conn_id, manager in self.connection_managers.items()
            }
        }