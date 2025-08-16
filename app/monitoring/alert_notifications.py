"""Alert notification handling and delivery system.

Manages notification channels, rate limiting, and delivery of alerts
through various channels like logs, email, Slack, webhooks, and database.
"""

import asyncio
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Any, Callable, Optional

from .alert_types import Alert, NotificationChannel, NotificationConfig, AlertLevel
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def create_default_notification_configs() -> Dict[NotificationChannel, NotificationConfig]:
    """Create default notification channel configurations."""
    return {
        NotificationChannel.LOG: _create_log_config(),
        NotificationChannel.EMAIL: _create_email_config(),
        NotificationChannel.SLACK: _create_slack_config(),
        NotificationChannel.WEBHOOK: _create_webhook_config(),
        NotificationChannel.DATABASE: _create_database_config()
    }


def _create_log_config() -> NotificationConfig:
    """Create log notification configuration."""
    return NotificationConfig(
        channel=NotificationChannel.LOG,
        enabled=True,
        rate_limit_per_hour=1000,
        min_level=AlertLevel.INFO
    )


def _create_email_config() -> NotificationConfig:
    """Create email notification configuration."""
    return NotificationConfig(
        channel=NotificationChannel.EMAIL,
        enabled=False,  # Disabled by default, needs configuration
        rate_limit_per_hour=20,
        min_level=AlertLevel.ERROR,
        config={"smtp_server": "", "recipients": []}
    )


def _create_slack_config() -> NotificationConfig:
    """Create Slack notification configuration."""
    return NotificationConfig(
        channel=NotificationChannel.SLACK,
        enabled=False,  # Disabled by default, needs configuration
        rate_limit_per_hour=50,
        min_level=AlertLevel.WARNING,
        config={"webhook_url": "", "channel": "#alerts"}
    )


def _create_webhook_config() -> NotificationConfig:
    """Create webhook notification configuration."""
    return NotificationConfig(
        channel=NotificationChannel.WEBHOOK,
        enabled=False,  # Disabled by default, needs configuration
        rate_limit_per_hour=100,
        min_level=AlertLevel.WARNING,
        config={"url": "", "headers": {}}
    )


def _create_database_config() -> NotificationConfig:
    """Create database notification configuration."""
    return NotificationConfig(
        channel=NotificationChannel.DATABASE,
        enabled=True,
        rate_limit_per_hour=500,
        min_level=AlertLevel.INFO
    )


class RateLimitManager:
    """Manages rate limiting for notification channels."""
    
    def __init__(self):
        """Initialize rate limit manager."""
        self.notification_rate_limits: Dict[NotificationChannel, List[datetime]] = {}
    
    def check_rate_limit(self, channel: NotificationChannel, config: NotificationConfig) -> bool:
        """Check if notification channel is within rate limits."""
        now = datetime.now(UTC)
        hour_ago = now - timedelta(hours=1)
        
        if channel not in self.notification_rate_limits:
            self.notification_rate_limits[channel] = []
        
        # Clean old entries
        self._clean_old_entries(channel, hour_ago)
        
        # Check limit
        if len(self.notification_rate_limits[channel]) >= config.rate_limit_per_hour:
            return False
        
        # Add current notification
        self.notification_rate_limits[channel].append(now)
        return True
    
    def _clean_old_entries(self, channel: NotificationChannel, cutoff_time: datetime) -> None:
        """Clean old rate limit entries."""
        self.notification_rate_limits[channel] = [
            ts for ts in self.notification_rate_limits[channel] if ts > cutoff_time
        ]


class NotificationSender:
    """Handles sending notifications through various channels."""
    
    def __init__(self):
        """Initialize notification sender."""
        self.notification_handlers: Dict[NotificationChannel, Callable] = {}
        self.notification_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000
    
    def register_handler(self, channel: NotificationChannel, handler: Callable) -> None:
        """Register custom notification handler for a channel."""
        self.notification_handlers[channel] = handler
        logger.info(f"Registered notification handler for {channel.value}")
    
    async def send_notification(
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
            await self._send_default_notification(alert, channel)
    
    async def _send_default_notification(self, alert: Alert, channel: NotificationChannel) -> None:
        """Send notification using default handlers."""
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
        """Store alert in database for audit and analysis."""
        try:
            from app.db.postgres import get_db_session
            async with get_db_session() as session:
                await self._store_alert_in_db(session, alert)
                await session.commit()
            logger.debug(f"Stored alert {alert.alert_id} in database")
        except Exception as e:
            logger.error(f"Failed to store alert {alert.alert_id}: {e}")
    
    async def _store_alert_in_db(self, session, alert: Alert) -> None:
        """Store alert record in database."""
        from sqlalchemy import text
        insert_query = text("""
            INSERT INTO system_alerts (alert_id, level, title, message, component, 
                                     timestamp, metadata, resolved)
            VALUES (:alert_id, :level, :title, :message, :component, 
                   :timestamp, :metadata, :resolved)
        """)
        
        await session.execute(insert_query, {
            'alert_id': alert.alert_id,
            'level': alert.level.value,
            'title': alert.title,
            'message': alert.message,
            'component': alert.agent_name or 'system',
            'timestamp': alert.timestamp,
            'metadata': str(alert.metadata) if alert.metadata else None,
            'resolved': alert.resolved
        })
    
    def track_notification(self, alert: Alert, channel: NotificationChannel) -> None:
        """Track sent notification for audit purposes."""
        self.notification_history.append({
            "alert_id": alert.alert_id,
            "channel": channel.value,
            "timestamp": datetime.now(UTC),
            "level": alert.level.value
        })
        
        # Keep only recent history
        if len(self.notification_history) > self.max_history_size:
            self.notification_history = self.notification_history[-self.max_history_size:]


class NotificationDeliveryManager:
    """Coordinates notification delivery across all channels."""
    
    def __init__(self):
        """Initialize delivery manager."""
        self.rate_limit_manager = RateLimitManager()
        self.notification_sender = NotificationSender()
    
    async def deliver_notifications(
        self, 
        alert: Alert, 
        channels: List[NotificationChannel],
        configs: Dict[NotificationChannel, NotificationConfig]
    ) -> None:
        """Deliver notifications through configured channels."""
        for channel in channels:
            config = configs.get(channel)
            
            if not config or not config.enabled:
                continue
            
            # Check minimum level
            if self._is_below_min_level(alert.level, config.min_level):
                continue
            
            # Check rate limits
            if not self.rate_limit_manager.check_rate_limit(channel, config):
                continue
            
            try:
                await self.notification_sender.send_notification(alert, channel, config)
                self.notification_sender.track_notification(alert, channel)
            except Exception as e:
                logger.error(f"Failed to send notification via {channel.value}: {e}")
    
    def _is_below_min_level(self, alert_level: AlertLevel, min_level: AlertLevel) -> bool:
        """Check if alert level is below minimum level."""
        level_order = {
            AlertLevel.INFO: 0,
            AlertLevel.WARNING: 1,
            AlertLevel.ERROR: 2,
            AlertLevel.CRITICAL: 3
        }
        return level_order.get(alert_level, 0) < level_order.get(min_level, 0)
    
    def register_notification_handler(
        self, 
        channel: NotificationChannel, 
        handler: Callable
    ) -> None:
        """Register custom notification handler."""
        self.notification_sender.register_handler(channel, handler)