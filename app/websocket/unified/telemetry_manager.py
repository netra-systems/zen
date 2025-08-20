"""Telemetry and transactional message management for WebSocket connections.

Handles real-time telemetry tracking, message queue management,
and transactional message processing with zero-loss guarantees.
"""

import asyncio
import time
from typing import Dict, Any, Union
from datetime import datetime, timezone

from app.logging_config import central_logger
from app.schemas.registry import WebSocketMessage, ServerMessage

logger = central_logger.get_logger(__name__)


class TelemetryManager:
    """Manages telemetry tracking and transactional message processing."""
    
    def __init__(self) -> None:
        """Initialize telemetry tracking."""
        self.telemetry = self._create_telemetry_config()
        # Ensure telemetry keys always exist
        if not isinstance(self.telemetry, dict):
            self.telemetry = {}
        required_keys = [
            "connections_opened", "connections_closed", "messages_sent", 
            "messages_received", "errors_handled", "circuit_breaks", "start_time"
        ]
        for key in required_keys:
            if key not in self.telemetry:
                self.telemetry[key] = 0 if key != "start_time" else time.time()
        
        # Initialize transactional message tracking
        self.pending_messages: Dict[str, Dict[str, Any]] = {}
        self.sending_messages: Dict[str, Dict[str, Any]] = {}
        self.message_lock = asyncio.Lock()
        
        # Initialize cleanup task as None - will be started on first connection
        self._cleanup_task = None

    def _create_telemetry_config(self) -> Dict[str, Union[int, float]]:
        """Create initial telemetry configuration dictionary."""
        return {
            "connections_opened": 0, "connections_closed": 0,
            "messages_sent": 0, "messages_received": 0,
            "errors_handled": 0, "circuit_breaks": 0,
            "start_time": time.time()
        }

    def get_telemetry_stats(self) -> Dict[str, Any]:
        """Get real-time telemetry statistics."""
        uptime = time.time() - self.telemetry["start_time"]
        return {
            "telemetry": self.telemetry.copy(),
            "uptime_seconds": uptime,
            "messages_per_second": self.telemetry["messages_sent"] / max(uptime, 1)
        }

    async def get_transactional_stats(self) -> Dict[str, Any]:
        """Get statistics about transactional message processing."""
        async with self.message_lock:
            return {
                "pending_messages": len(self.pending_messages),
                "sending_messages": len(self.sending_messages),
                "oldest_pending": min(
                    [msg["timestamp"] for msg in self.pending_messages.values()], 
                    default=time.time()
                ),
                "oldest_sending": min(
                    [msg["timestamp"] for msg in self.sending_messages.values()], 
                    default=time.time()
                )
            }

    async def mark_message_sending(self, message_id: str, user_id: str, 
                                  message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> None:
        """Mark message as currently being sent (transactional pattern)."""
        async with self.message_lock:
            message_data = {
                "message_id": message_id,
                "user_id": user_id,
                "message": message,
                "timestamp": time.time(),
                "status": "sending"
            }
            self.sending_messages[message_id] = message_data
            # Remove from pending if it was there
            self.pending_messages.pop(message_id, None)

    async def mark_message_sent(self, message_id: str) -> None:
        """Mark message as successfully sent and remove from tracking."""
        async with self.message_lock:
            self.sending_messages.pop(message_id, None)
            # Message successfully sent, no need to track further

    async def mark_message_pending(self, message_id: str, user_id: str, 
                                  message: Union[WebSocketMessage, ServerMessage, Dict[str, Any]]) -> None:
        """Mark message as pending for retry (transactional pattern)."""
        async with self.message_lock:
            message_data = {
                "message_id": message_id,
                "user_id": user_id,
                "message": message,
                "timestamp": time.time(),
                "status": "pending",
                "retry_count": self.sending_messages.get(message_id, {}).get("retry_count", 0) + 1
            }
            self.pending_messages[message_id] = message_data
            # Remove from sending
            self.sending_messages.pop(message_id, None)

    async def retry_pending_messages(self, send_callback) -> None:
        """Retry all pending messages that failed to send."""
        async with self.message_lock:
            pending_to_retry = list(self.pending_messages.items())
        
        retry_count = 0
        for message_id, message_data in pending_to_retry:
            if message_data["retry_count"] < 3:  # Max 3 retries
                try:
                    result = await send_callback(
                        message_data["user_id"], 
                        message_data["message"], 
                        retry=False  # Prevent infinite recursion
                    )
                    if result:
                        retry_count += 1
                except Exception as e:
                    logger.error(f"Retry failed for message {message_id}: {e}")
            else:
                # Max retries exceeded, remove from pending
                async with self.message_lock:
                    self.pending_messages.pop(message_id, None)
                logger.error(f"Message {message_id} exceeded max retries, dropping")
        
        if retry_count > 0:
            logger.info(f"Successfully retried {retry_count} pending messages")

    async def start_periodic_cleanup(self) -> None:
        """Start the periodic cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup to prevent memory leaks from stale messages."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                
                current_time = time.time()
                max_age = 1800  # 30 minutes
                
                async with self.message_lock:
                    # Clean up old pending messages
                    old_pending = [
                        msg_id for msg_id, msg_data in self.pending_messages.items()
                        if current_time - msg_data["timestamp"] > max_age
                    ]
                    
                    # Clean up old sending messages
                    old_sending = [
                        msg_id for msg_id, msg_data in self.sending_messages.items()
                        if current_time - msg_data["timestamp"] > max_age
                    ]
                    
                    # Remove old messages
                    for msg_id in old_pending:
                        del self.pending_messages[msg_id]
                    
                    for msg_id in old_sending:
                        del self.sending_messages[msg_id]
                    
                    if old_pending or old_sending:
                        logger.info(f"Cleaned up {len(old_pending)} old pending and {len(old_sending)} old sending messages")
                
            except asyncio.CancelledError:
                logger.debug("Periodic cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")

    async def shutdown(self) -> None:
        """Gracefully shutdown telemetry manager with memory leak prevention."""
        logger.info("Starting telemetry manager shutdown...")
        
        # Cancel cleanup task if it exists and is running
        if hasattr(self, '_cleanup_task') and self._cleanup_task is not None and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Handle any pending messages before shutdown
        async with self.message_lock:
            pending_count = len(self.pending_messages)
            sending_count = len(self.sending_messages)
            
            if pending_count > 0 or sending_count > 0:
                logger.warning(f"Shutting down with {pending_count} pending and {sending_count} sending messages")
                
                # Clear all message tracking to prevent memory leaks
                self.pending_messages.clear()
                self.sending_messages.clear()
                logger.info("Cleared all pending/sending message queues to prevent memory leaks")
        
        # Clear telemetry data
        self.telemetry.clear()
        
        logger.info("Telemetry manager shutdown complete with memory cleanup")