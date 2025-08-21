"""Alert notification handling and delivery system.

Manages notification channels, rate limiting, and delivery of alerts
through various channels like logs, email, Slack, webhooks, and database.
"""

import asyncio
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Any, Callable, Optional

from netra_backend.app.monitoring.alert_types import Alert, NotificationChannel, NotificationConfig, AlertLevel
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


def create_default_notification_configs() -> Dict[NotificationChannel, NotificationConfig]:
    """Create default notification channel configurations."""
    return _build_all_notification_configs()

def _build_all_notification_configs() -> Dict[NotificationChannel, NotificationConfig]:
    """Build all notification channel configurations."""
    basic_configs = _build_basic_configs()
    extended_configs = _build_extended_configs()
    return {**basic_configs, **extended_configs}

def _build_basic_configs() -> Dict[NotificationChannel, NotificationConfig]:
    """Build basic notification configurations."""
    return {
        NotificationChannel.LOG: _create_log_config(),
        NotificationChannel.EMAIL: _create_email_config(),
        NotificationChannel.SLACK: _create_slack_config()
    }

def _build_extended_configs() -> Dict[NotificationChannel, NotificationConfig]:
    """Build extended notification configurations."""
    return {
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
    config_params = _get_email_config_params()
    return NotificationConfig(**config_params)

def _get_email_config_params() -> Dict[str, Any]:
    """Get email configuration parameters."""
    return {
        "channel": NotificationChannel.EMAIL, "enabled": False,
        "rate_limit_per_hour": 20, "min_level": AlertLevel.ERROR,
        "config": _get_email_default_config()
    }

def _get_email_default_config() -> Dict[str, Any]:
    """Get default email configuration."""
    return {"smtp_server": "", "recipients": []}


def _create_slack_config() -> NotificationConfig:
    """Create Slack notification configuration."""
    config_params = _get_slack_config_params()
    return NotificationConfig(**config_params)

def _get_slack_config_params() -> Dict[str, Any]:
    """Get Slack configuration parameters."""
    return {
        "channel": NotificationChannel.SLACK, "enabled": False,
        "rate_limit_per_hour": 50, "min_level": AlertLevel.WARNING,
        "config": _get_slack_default_config()
    }

def _get_slack_default_config() -> Dict[str, Any]:
    """Get default Slack configuration."""
    return {"webhook_url": "", "channel": "#alerts"}


def _create_webhook_config() -> NotificationConfig:
    """Create webhook notification configuration."""
    config_params = _get_webhook_config_params()
    return NotificationConfig(**config_params)

def _get_webhook_config_params() -> Dict[str, Any]:
    """Get webhook configuration parameters."""
    return {
        "channel": NotificationChannel.WEBHOOK, "enabled": False,
        "rate_limit_per_hour": 100, "min_level": AlertLevel.WARNING,
        "config": _get_webhook_default_config()
    }

def _get_webhook_default_config() -> Dict[str, Any]:
    """Get default webhook configuration."""
    return {"url": "", "headers": {}}

def _create_simple_config(channel: NotificationChannel, enabled: bool, rate_limit: int, level: AlertLevel) -> NotificationConfig:
    """Create simple notification config."""
    return NotificationConfig(
        channel=channel,
        enabled=enabled,
        rate_limit_per_hour=rate_limit,
        min_level=level
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
        
        self._ensure_channel_exists(channel)
        self._clean_old_entries(channel, hour_ago)
        return self._check_and_update_limit(channel, config, now)

    def _ensure_channel_exists(self, channel: NotificationChannel) -> None:
        """Ensure channel exists in rate limits."""
        if channel not in self.notification_rate_limits:
            self.notification_rate_limits[channel] = []

    def _is_over_limit(self, channel: NotificationChannel, config: NotificationConfig) -> bool:
        """Check if channel is over rate limit."""
        return len(self.notification_rate_limits[channel]) >= config.rate_limit_per_hour
    
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
        log_level_map = self._get_log_level_mapping()
        log_func = log_level_map.get(alert.level, logger.info)
        message = self._format_log_message(alert)
        log_func(message)

    def _get_log_level_mapping(self) -> Dict[AlertLevel, Callable]:
        """Get mapping of alert levels to log functions."""
        return {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }

    def _format_log_message(self, alert: Alert) -> str:
        """Format alert message for logging."""
        return f"ALERT [{alert.level.value.upper()}] {alert.title}: {alert.message}"
    
    async def _send_database_notification(self, alert: Alert) -> None:
        """Store alert in database for audit and analysis."""
        try:
            await self._store_alert_safely(alert)
            logger.debug(f"Stored alert {alert.alert_id} in database")
        except Exception as e:
            logger.error(f"Failed to store alert {alert.alert_id}: {e}")

    async def _store_alert_safely(self, alert: Alert) -> None:
        """Store alert in database with session management."""
        from netra_backend.app.db.postgres import get_db_session
        async with get_db_session() as session:
            await self._store_alert_in_db(session, alert)
            await session.commit()
    
    async def _store_alert_in_db(self, session, alert: Alert) -> None:
        """Store alert record in database."""
        from sqlalchemy import text
        insert_query = self._get_insert_query()
        alert_data = self._prepare_alert_data(alert)
        await session.execute(insert_query, alert_data)

    def _get_insert_query(self) -> Any:
        """Get database insert query for alerts."""
        from sqlalchemy import text
        return text("""
            INSERT INTO system_alerts (alert_id, level, title, message, component, 
                                     timestamp, metadata, resolved)
            VALUES (:alert_id, :level, :title, :message, :component, 
                   :timestamp, :metadata, :resolved)
        """)

    def _prepare_alert_data(self, alert: Alert) -> Dict[str, Any]:
        """Prepare alert data for database insertion."""
        basic_data = self._get_alert_basic_data(alert)
        metadata_data = self._get_alert_metadata_data(alert)
        return {**basic_data, **metadata_data}

    def _get_alert_basic_data(self, alert: Alert) -> Dict[str, Any]:
        """Get basic alert data fields."""
        return {
            'alert_id': alert.alert_id,
            'level': alert.level.value,
            'title': alert.title,
            'message': alert.message
        }

    def _get_alert_metadata_data(self, alert: Alert) -> Dict[str, Any]:
        """Get alert metadata and additional fields."""
        return {
            'component': alert.agent_name or 'system',
            'timestamp': alert.timestamp,
            'metadata': str(alert.metadata) if alert.metadata else None,
            'resolved': alert.resolved
        }
    
    def track_notification(self, alert: Alert, channel: NotificationChannel) -> None:
        """Track sent notification for audit purposes."""
        notification_record = self._create_notification_record(alert, channel)
        self.notification_history.append(notification_record)
        self._trim_notification_history()

    def _create_notification_record(self, alert: Alert, channel: NotificationChannel) -> Dict[str, Any]:
        """Create notification record for tracking."""
        return {
            "alert_id": alert.alert_id,
            "channel": channel.value,
            "timestamp": datetime.now(UTC),
            "level": alert.level.value
        }

    def _trim_notification_history(self) -> None:
        """Trim notification history to max size."""
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
            await self._process_channel_notification(alert, channel, configs)

    def _should_deliver_notification(
        self, 
        alert: Alert, 
        channel: NotificationChannel, 
        config: Optional[NotificationConfig]
    ) -> bool:
        """Check if notification should be delivered."""
        if not config or not config.enabled:
            return False
        
        if self._is_below_min_level(alert.level, config.min_level):
            return False
        
        return self.rate_limit_manager.check_rate_limit(channel, config)

    async def _send_single_notification(
        self, 
        alert: Alert, 
        channel: NotificationChannel, 
        config: NotificationConfig
    ) -> None:
        """Send single notification with error handling."""
        try:
            await self.notification_sender.send_notification(alert, channel, config)
            self.notification_sender.track_notification(alert, channel)
        except Exception as e:
            logger.error(f"Failed to send notification via {channel.value}: {e}")
    
    def _is_below_min_level(self, alert_level: AlertLevel, min_level: AlertLevel) -> bool:
        """Check if alert level is below minimum level."""
        level_order = self._get_alert_level_order()
        alert_priority = level_order.get(alert_level, 0)
        min_priority = level_order.get(min_level, 0)
        return alert_priority < min_priority

    def _get_alert_level_order(self) -> Dict[AlertLevel, int]:
        """Get alert level priority order."""
        return {
            AlertLevel.INFO: 0,
            AlertLevel.WARNING: 1,
            AlertLevel.ERROR: 2,
            AlertLevel.CRITICAL: 3
        }

    def _check_and_update_limit(self, channel: NotificationChannel, config: NotificationConfig, now: datetime) -> bool:
        """Check rate limit and update if within bounds."""
        if self._is_over_limit(channel, config):
            return False
        
        self.notification_rate_limits[channel].append(now)
        return True

    async def _process_channel_notification(
        self, 
        alert: Alert, 
        channel: NotificationChannel, 
        configs: Dict[NotificationChannel, NotificationConfig]
    ) -> None:
        """Process notification for a single channel."""
        config = configs.get(channel)
        await self._handle_channel_delivery(alert, channel, config)

    async def _handle_channel_delivery(
        self, alert: Alert, channel: NotificationChannel, config: Optional[NotificationConfig]
    ) -> None:
        """Handle delivery for specific channel."""
        if not self._should_deliver_notification(alert, channel, config):
            return
        await self._send_single_notification(alert, channel, config)
    
    def register_notification_handler(
        self, 
        channel: NotificationChannel, 
        handler: Callable
    ) -> None:
        """Register custom notification handler."""
        self.notification_sender.register_handler(channel, handler)