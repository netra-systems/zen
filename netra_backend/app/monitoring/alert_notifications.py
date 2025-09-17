"""
Alert notification delivery system.
Handles delivery of alerts through various notification channels.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, UTC

from netra_backend.app.logging_config import central_logger
from netra_backend.app.monitoring.alert_models import Alert, NotificationChannel

logger = central_logger.get_logger(__name__)


class NotificationDeliveryManager:
    """Manages delivery of alerts through notification channels."""
    
    def __init__(self):
        self._channels: List[NotificationChannel] = []
        self._delivery_history: List[Dict[str, Any]] = []
        logger.debug("Initialized NotificationDeliveryManager")
    
    async def add_channel(self, channel: NotificationChannel) -> None:
        """Add a notification channel."""
        self._channels.append(channel)
        logger.info(f"Added notification channel: {channel.name} ({channel.channel_type})")
    
    async def remove_channel(self, channel_id: str) -> bool:
        """Remove a notification channel by ID."""
        initial_count = len(self._channels)
        self._channels = [c for c in self._channels if c.channel_id != channel_id]
        removed = len(self._channels) < initial_count
        if removed:
            logger.info(f"Removed notification channel: {channel_id}")
        return removed
    
    async def deliver_alert(self, alert: Alert) -> Dict[str, bool]:
        """Deliver alert to all configured channels."""
        results = {}
        
        for channel in self._channels:
            if self._should_deliver_to_channel(alert, channel):
                try:
                    success = await self._deliver_to_channel(alert, channel)
                    results[channel.channel_id] = success
                    
                    # Record delivery attempt
                    self._delivery_history.append({
                        "alert_id": alert.alert_id,
                        "channel_id": channel.channel_id,
                        "success": success,
                        "timestamp": datetime.now(UTC)
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to deliver alert {alert.alert_id} to channel {channel.channel_id}: {e}")
                    results[channel.channel_id] = False
        
        return results
    
    def _should_deliver_to_channel(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Check if alert should be delivered to this channel."""
        # Basic filtering - deliver if alert level meets channel minimum
        if hasattr(channel, 'min_alert_level'):
            alert_level_value = self._get_alert_level_value(alert.level)
            channel_level_value = self._get_alert_level_value(channel.min_alert_level)
            return alert_level_value >= channel_level_value
        
        # Default: deliver to all channels
        return True
    
    def _get_alert_level_value(self, level) -> int:
        """Get numeric value for alert level comparison."""
        level_values = {
            "INFO": 1,
            "WARNING": 2,
            "ERROR": 3,
            "CRITICAL": 4
        }
        if hasattr(level, 'value'):
            return level_values.get(level.value, 1)
        return level_values.get(str(level).upper(), 1)
    
    async def _deliver_to_channel(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Deliver alert to specific channel."""
        # This is a stub implementation - in real system would integrate with
        # actual notification services (email, Slack, etc.)
        
        message = self._format_alert_message(alert, channel)
        
        logger.info(f"Delivering alert to {channel.channel_type} channel '{channel.name}': {message}")
        
        # Simulate successful delivery
        return True
    
    def _format_alert_message(self, alert: Alert, channel: NotificationChannel) -> str:
        """Format alert message for specific channel."""
        return (
            f"Alert: {alert.title}\n"
            f"Level: {alert.level}\n"
            f"Message: {alert.message}\n"
            f"Agent: {alert.agent_name or 'System'}\n"
            f"Time: {alert.timestamp}"
        )
    
    async def get_delivery_stats(self) -> Dict[str, Any]:
        """Get delivery statistics."""
        total_deliveries = len(self._delivery_history)
        successful_deliveries = len([d for d in self._delivery_history if d['success']])
        
        return {
            "total_channels": len(self._channels),
            "total_deliveries": total_deliveries,
            "successful_deliveries": successful_deliveries,
            "failure_rate": (total_deliveries - successful_deliveries) / max(total_deliveries, 1),
            "recent_deliveries": self._delivery_history[-10:] if self._delivery_history else []
        }


__all__ = [
    "NotificationDeliveryManager",
]