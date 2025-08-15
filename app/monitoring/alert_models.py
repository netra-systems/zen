"""
Alert management models and configurations.
Contains data classes and enums for the alert system.
"""

from datetime import datetime, UTC
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    """Available notification channels."""
    LOG = "log"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    DATABASE = "database"


@dataclass
class AlertRule:
    """Configuration for an alert rule."""
    rule_id: str
    name: str
    description: str
    condition: str  # Python expression string
    level: AlertLevel
    threshold_value: float
    time_window_minutes: int = 5
    evaluation_interval_seconds: int = 30
    cooldown_minutes: int = 15
    channels: List[NotificationChannel] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Alert instance."""
    alert_id: str
    rule_id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    agent_name: Optional[str] = None
    metric_name: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    suppressed: bool = False
    suppression_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationConfig:
    """Configuration for notification channels."""
    channel: NotificationChannel
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    rate_limit_per_hour: int = 100
    min_level: AlertLevel = AlertLevel.INFO


def create_default_alert_rules() -> List[AlertRule]:
    """Create default alert rules for common scenarios."""
    return [
        AlertRule(
            rule_id="agent_high_error_rate",
            name="High Agent Error Rate",
            description="Agent error rate exceeds threshold",
            condition="error_rate > threshold_value",
            level=AlertLevel.ERROR,
            threshold_value=0.2,  # 20% error rate
            time_window_minutes=5,
            channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
        ),
        AlertRule(
            rule_id="agent_critical_error_rate",
            name="Critical Agent Error Rate",
            description="Agent error rate critically high",
            condition="error_rate > threshold_value",
            level=AlertLevel.CRITICAL,
            threshold_value=0.5,  # 50% error rate
            time_window_minutes=3,
            channels=[NotificationChannel.LOG, NotificationChannel.EMAIL, NotificationChannel.SLACK]
        ),
        AlertRule(
            rule_id="agent_timeout_spike",
            name="Agent Timeout Spike",
            description="High number of agent timeouts",
            condition="timeout_count > threshold_value",
            level=AlertLevel.WARNING,
            threshold_value=5,  # 5 timeouts in window
            time_window_minutes=5,
            channels=[NotificationChannel.LOG]
        ),
        AlertRule(
            rule_id="agent_avg_execution_time_high",
            name="High Agent Execution Time",
            description="Average execution time exceeds threshold",
            condition="avg_execution_time_ms > threshold_value",
            level=AlertLevel.WARNING,
            threshold_value=30000,  # 30 seconds
            time_window_minutes=10,
            channels=[NotificationChannel.LOG]
        ),
        AlertRule(
            rule_id="agent_validation_error_spike",
            name="Validation Error Spike",
            description="High number of validation errors",
            condition="validation_error_count > threshold_value",
            level=AlertLevel.ERROR,
            threshold_value=10,  # 10 validation errors
            time_window_minutes=5,
            channels=[NotificationChannel.LOG, NotificationChannel.SLACK]
        ),
        AlertRule(
            rule_id="system_wide_failure_rate",
            name="System-wide High Failure Rate",
            description="Overall system failure rate is high",
            condition="system_error_rate > threshold_value",
            level=AlertLevel.CRITICAL,
            threshold_value=0.3,  # 30% system-wide error rate
            time_window_minutes=5,
            channels=[NotificationChannel.LOG, NotificationChannel.EMAIL, NotificationChannel.SLACK]
        )
    ]


def create_default_notification_configs() -> Dict[NotificationChannel, NotificationConfig]:
    """Create default notification channel configurations."""
    return {
        NotificationChannel.LOG: NotificationConfig(
            channel=NotificationChannel.LOG,
            enabled=True,
            rate_limit_per_hour=1000,
            min_level=AlertLevel.INFO
        ),
        NotificationChannel.EMAIL: NotificationConfig(
            channel=NotificationChannel.EMAIL,
            enabled=False,  # Disabled by default, needs configuration
            rate_limit_per_hour=20,
            min_level=AlertLevel.ERROR,
            config={"smtp_server": "", "recipients": []}
        ),
        NotificationChannel.SLACK: NotificationConfig(
            channel=NotificationChannel.SLACK,
            enabled=False,  # Disabled by default, needs configuration
            rate_limit_per_hour=50,
            min_level=AlertLevel.WARNING,
            config={"webhook_url": "", "channel": "#alerts"}
        ),
        NotificationChannel.WEBHOOK: NotificationConfig(
            channel=NotificationChannel.WEBHOOK,
            enabled=False,  # Disabled by default, needs configuration
            rate_limit_per_hour=100,
            min_level=AlertLevel.WARNING,
            config={"url": "", "headers": {}}
        ),
        NotificationChannel.DATABASE: NotificationConfig(
            channel=NotificationChannel.DATABASE,
            enabled=True,
            rate_limit_per_hour=500,
            min_level=AlertLevel.INFO
        )
    }