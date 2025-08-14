"""
Alert notification handling and delivery.
Manages notification channels and rate limiting.
"""

import asyncio
from typing import Dict, Any, List, Callable
from datetime import datetime, UTC, timedelta

from app.logging_config import central_logger
from .alert_models import Alert, NotificationChannel, NotificationConfig, AlertLevel

logger = central_logger.get_logger(__name__)


class NotificationManager:
    """Manages notification delivery and rate limiting."""
    
    def __init__(self):
        self.notification_history: List[Dict[str, Any]] = []
        self.notification_rate_limits: Dict[NotificationChannel, List[datetime]] = {}
        self.notification_handlers: Dict[NotificationChannel, Callable] = {}
    
    async def send_notifications(
        self, 
        alert: Alert, 
        channels: List[NotificationChannel],
        notification_configs: Dict[NotificationChannel, NotificationConfig]
    ) -> None:
        """Send notifications through configured channels."""
        for channel in channels:
            config = notification_configs.get(channel)
            
            if not config or not config.enabled:
                continue
            
            # Check minimum level
            if self._is_below_min_level(alert.level, config.min_level):
                continue
            
            # Check rate limits
            if not await self._check_rate_limit(channel, config):
                continue
            
            try:
                await self._send_notification(alert, channel, config)
                self._track_notification(alert, channel)
            except Exception as e:
                logger.error(f"Failed to send notification via {channel.value}: {e}")
    
    def _is_below_min_level(self, alert_level: AlertLevel, min_level: AlertLevel) -> bool:
        """Check if alert level is below minimum level for channel."""
        level_priority = {
            AlertLevel.INFO: 1,
            AlertLevel.WARNING: 2,
            AlertLevel.ERROR: 3,
            AlertLevel.CRITICAL: 4
        }
        return level_priority.get(alert_level, 1) < level_priority.get(min_level, 1)
    
    async def _check_rate_limit(self, channel: NotificationChannel, config: NotificationConfig) -> bool:
        """Check if notification channel is within rate limits."""
        now = datetime.now(UTC)
        hour_ago = now - timedelta(hours=1)
        
        if channel not in self.notification_rate_limits:
            self.notification_rate_limits[channel] = []
        
        # Clean old entries
        self.notification_rate_limits[channel] = [
            ts for ts in self.notification_rate_limits[channel] if ts > hour_ago
        ]
        
        # Check limit
        if len(self.notification_rate_limits[channel]) >= config.rate_limit_per_hour:
            return False
        
        # Add current notification
        self.notification_rate_limits[channel].append(now)
        return True
    
    async def _send_notification(
        self, 
        alert: Alert, 
        channel: NotificationChannel, 
        config: NotificationConfig
    ) -> None:
        """Send notification through specific channel."""
        handler = self.notification_handlers.get(channel)
        
        if handler:
            await handler(alert, config)
        else:
            # Default handlers
            if channel == NotificationChannel.LOG:
                await self._send_log_notification(alert)
            elif channel == NotificationChannel.DATABASE:
                await self._send_database_notification(alert)
            # Other channels would need custom handlers
    
    async def _send_log_notification(self, alert: Alert) -> None:
        """Send notification to log."""
        log_level_map = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }
        
        log_func = log_level_map.get(alert.level, logger.info)
        log_func(f"ALERT [{alert.level.value.upper()}] {alert.title}: {alert.message}")
    
    async def _send_database_notification(self, alert: Alert) -> None:
        """Store alert in database (placeholder for actual implementation)."""
        # This would store the alert in the database
        # Implementation depends on the database schema
        logger.debug(f"Storing alert {alert.alert_id} in database")
    
    def _track_notification(self, alert: Alert, channel: NotificationChannel) -> None:
        """Track sent notification for audit purposes."""
        self.notification_history.append({
            "alert_id": alert.alert_id,
            "channel": channel.value,
            "timestamp": datetime.now(UTC),
            "level": alert.level.value
        })
        
        # Keep only recent history
        if len(self.notification_history) > 1000:
            self.notification_history = self.notification_history[-1000:]
    
    def register_notification_handler(
        self, 
        channel: NotificationChannel, 
        handler: Callable
    ) -> None:
        """Register custom notification handler for a channel."""
        self.notification_handlers[channel] = handler
        logger.info(f"Registered notification handler for {channel.value}")
    
    def get_notification_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get notification history for specified time period."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        
        return [
            entry for entry in self.notification_history
            if entry["timestamp"] > cutoff_time
        ]