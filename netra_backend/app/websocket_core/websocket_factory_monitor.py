"""WebSocket Factory Monitor - Real-time Monitoring and Alerting

This module provides real-time monitoring and alerting for the WebSocket Manager Factory
to prevent and respond to resource exhaustion emergencies.

Features:
- Real-time health monitoring and alerting
- Threshold-based proactive intervention
- Resource exhaustion prediction
- Emergency response coordination
- Comprehensive metrics collection
- Dashboard-ready monitoring data

Business Value Justification (BVJ):
- Segment: Enterprise (protects $500K+ ARR)
- Business Goal: Proactive resource management and incident prevention
- Value Impact: Prevents permanent AI chat blocking before it happens
- Revenue Impact: Maintains service availability during peak usage
"""

import asyncio
import time
import threading
from enum import Enum
from typing import Dict, Optional, Set, Any, List, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class AlertLevel(Enum):
    """Alert severity levels for monitoring"""
    INFO = "info"           # Normal operational information
    WARNING = "warning"     # Resource usage approaching limits
    CRITICAL = "critical"   # Immediate attention required
    EMERGENCY = "emergency" # Service degradation imminent


class MonitoringState(Enum):
    """Monitor operational states"""
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class AlertThreshold:
    """Configuration for monitoring thresholds"""
    name: str
    warning_threshold: float = 0.7    # 70% of limit
    critical_threshold: float = 0.85  # 85% of limit
    emergency_threshold: float = 0.95 # 95% of limit
    enabled: bool = True


@dataclass
class MonitoringMetrics:
    """Real-time metrics for factory monitoring"""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Factory metrics
    total_managers: int = 0
    total_users: int = 0
    average_managers_per_user: float = 0.0
    peak_managers_per_user: int = 0

    # Health metrics
    healthy_managers: int = 0
    idle_managers: int = 0
    zombie_managers: int = 0
    inactive_managers: int = 0
    unknown_managers: int = 0

    # Performance metrics
    cleanup_events_total: int = 0
    emergency_cleanups_total: int = 0
    zombie_detections_total: int = 0
    forced_removals_total: int = 0
    average_cleanup_duration: float = 0.0

    # Resource utilization
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    def health_ratio(self) -> float:
        """Calculate overall health ratio"""
        if self.total_managers == 0:
            return 1.0
        return self.healthy_managers / self.total_managers

    def zombie_ratio(self) -> float:
        """Calculate zombie manager ratio"""
        if self.total_managers == 0:
            return 0.0
        return self.zombie_managers / self.total_managers


@dataclass
class Alert:
    """Monitoring alert"""
    level: AlertLevel
    category: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolution_time: Optional[datetime] = None

    def resolve(self):
        """Mark alert as resolved"""
        self.resolved = True
        self.resolution_time = datetime.now(timezone.utc)

    def age_seconds(self) -> float:
        """Get alert age in seconds"""
        return (datetime.now(timezone.utc) - self.timestamp).total_seconds()


class WebSocketFactoryMonitor:
    """
    Real-time Monitor for WebSocket Manager Factory

    Provides:
    - Continuous health monitoring
    - Threshold-based alerting
    - Proactive resource management
    - Emergency response coordination
    - Comprehensive metrics collection
    """

    def __init__(self, factory=None, monitoring_interval: float = 30.0):
        self.factory = factory
        self.monitoring_interval = monitoring_interval
        self.state = MonitoringState.STOPPED

        # Monitoring data
        self.current_metrics = MonitoringMetrics()
        self.metrics_history: List[MonitoringMetrics] = []
        self.active_alerts: List[Alert] = []
        self.resolved_alerts: List[Alert] = []

        # Configuration
        self.thresholds = {
            'managers_per_user': AlertThreshold(
                name='managers_per_user',
                warning_threshold=14,   # 70% of 20
                critical_threshold=17,  # 85% of 20
                emergency_threshold=19  # 95% of 20
            ),
            'zombie_ratio': AlertThreshold(
                name='zombie_ratio',
                warning_threshold=0.2,  # 20% zombies
                critical_threshold=0.4, # 40% zombies
                emergency_threshold=0.6 # 60% zombies
            ),
            'health_ratio': AlertThreshold(
                name='health_ratio',
                warning_threshold=0.8,  # 80% healthy (reverse threshold)
                critical_threshold=0.6, # 60% healthy
                emergency_threshold=0.4 # 40% healthy
            )
        }

        # Alert handlers
        self.alert_handlers: List[Callable[[Alert], None]] = []

        # Threading
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._metrics_lock = threading.RLock()

        logger.info(f"WebSocketFactoryMonitor initialized with {self.monitoring_interval}s interval")

    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add custom alert handler"""
        self.alert_handlers.append(handler)
        logger.debug(f"Added alert handler: {handler.__name__}")

    def remove_alert_handler(self, handler: Callable[[Alert], None]):
        """Remove alert handler"""
        if handler in self.alert_handlers:
            self.alert_handlers.remove(handler)
            logger.debug(f"Removed alert handler: {handler.__name__}")

    def start_monitoring(self):
        """Start the monitoring service"""
        if self.state == MonitoringState.RUNNING:
            logger.warning("Monitor is already running")
            return

        self.state = MonitoringState.STARTING
        self._stop_event.clear()

        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            name="WebSocketFactoryMonitor",
            daemon=True
        )
        self._monitor_thread.start()

        self.state = MonitoringState.RUNNING
        logger.info("WebSocket Factory Monitor started")

    def stop_monitoring(self):
        """Stop the monitoring service"""
        if self.state not in [MonitoringState.RUNNING, MonitoringState.PAUSED]:
            logger.warning(f"Cannot stop monitor in state: {self.state}")
            return

        self.state = MonitoringState.STOPPING
        self._stop_event.set()

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
            if self._monitor_thread.is_alive():
                logger.error("Monitor thread did not stop gracefully")

        self.state = MonitoringState.STOPPED
        logger.info("WebSocket Factory Monitor stopped")

    def pause_monitoring(self):
        """Pause monitoring temporarily"""
        if self.state == MonitoringState.RUNNING:
            self.state = MonitoringState.PAUSED
            logger.info("WebSocket Factory Monitor paused")

    def resume_monitoring(self):
        """Resume monitoring after pause"""
        if self.state == MonitoringState.PAUSED:
            self.state = MonitoringState.RUNNING
            logger.info("WebSocket Factory Monitor resumed")

    def _monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Monitoring loop started")

        try:
            while not self._stop_event.is_set():
                if self.state == MonitoringState.RUNNING:
                    try:
                        # Collect metrics
                        self._collect_metrics()

                        # Check thresholds and generate alerts
                        self._check_thresholds()

                        # Clean up old data
                        self._cleanup_old_data()

                    except Exception as e:
                        logger.error(f"Error in monitoring loop: {e}")
                        self._create_alert(
                            AlertLevel.CRITICAL,
                            "monitor_error",
                            f"Monitoring loop error: {e}",
                            {"error_type": type(e).__name__, "error_details": str(e)}
                        )

                # Wait for next interval
                self._stop_event.wait(self.monitoring_interval)

        except Exception as e:
            logger.error(f"Fatal error in monitoring loop: {e}")
            self.state = MonitoringState.ERROR

        logger.info("Monitoring loop ended")

    def _collect_metrics(self):
        """Collect current metrics from factory"""
        try:
            metrics = MonitoringMetrics()

            if self.factory:
                # Get factory status
                factory_status = self.factory.get_factory_status()

                metrics.total_managers = factory_status.get('total_managers', 0)
                metrics.total_users = factory_status.get('users_count', 0)

                # Calculate average managers per user
                if metrics.total_users > 0:
                    metrics.average_managers_per_user = metrics.total_managers / metrics.total_users

                # Get peak managers per user
                managers_by_user = factory_status.get('managers_by_user', {})
                if managers_by_user:
                    metrics.peak_managers_per_user = max(managers_by_user.values())

                # Get cleanup metrics
                cleanup_metrics = factory_status.get('cleanup_metrics', {})
                metrics.cleanup_events_total = cleanup_metrics.get('total_cleanups', 0)
                metrics.emergency_cleanups_total = cleanup_metrics.get('emergency_cleanups', 0)
                metrics.zombie_detections_total = cleanup_metrics.get('zombie_detections', 0)
                metrics.forced_removals_total = cleanup_metrics.get('forced_removals', 0)
                metrics.average_cleanup_duration = cleanup_metrics.get('average_cleanup_duration', 0.0)

                # Get health summary
                try:
                    health_report = asyncio.run(self.factory.health_check_all_managers())
                    metrics.healthy_managers = health_report.get('healthy_managers', 0)
                    metrics.idle_managers = health_report.get('idle_managers', 0)
                    metrics.zombie_managers = health_report.get('zombie_managers', 0)
                    metrics.inactive_managers = health_report.get('inactive_managers', 0)
                    metrics.unknown_managers = health_report.get('unknown_managers', 0)
                except Exception as e:
                    logger.warning(f"Could not get health report: {e}")

            # Collect system metrics
            self._collect_system_metrics(metrics)

            # Store metrics
            with self._metrics_lock:
                self.current_metrics = metrics
                self.metrics_history.append(metrics)

            logger.debug(f"Collected metrics: {metrics.total_managers} managers, {metrics.healthy_managers} healthy")

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")

    def _collect_system_metrics(self, metrics: MonitoringMetrics):
        """Collect system resource metrics"""
        try:
            import psutil

            # Memory usage
            process = psutil.Process()
            memory_info = process.memory_info()
            metrics.memory_usage_mb = memory_info.rss / 1024 / 1024  # Convert to MB

            # CPU usage
            metrics.cpu_usage_percent = process.cpu_percent()

        except ImportError:
            # psutil not available
            pass
        except Exception as e:
            logger.warning(f"Error collecting system metrics: {e}")

    def _check_thresholds(self):
        """Check metrics against thresholds and generate alerts"""
        metrics = self.current_metrics

        # Check managers per user threshold
        if metrics.peak_managers_per_user > 0:
            self._check_threshold(
                'managers_per_user',
                metrics.peak_managers_per_user,
                {
                    'peak_managers': metrics.peak_managers_per_user,
                    'total_managers': metrics.total_managers,
                    'total_users': metrics.total_users
                }
            )

        # Check zombie ratio threshold
        zombie_ratio = metrics.zombie_ratio()
        if zombie_ratio > 0:
            self._check_threshold(
                'zombie_ratio',
                zombie_ratio,
                {
                    'zombie_managers': metrics.zombie_managers,
                    'total_managers': metrics.total_managers,
                    'zombie_ratio': zombie_ratio
                }
            )

        # Check health ratio threshold (reverse logic - lower is worse)
        health_ratio = metrics.health_ratio()
        threshold_config = self.thresholds['health_ratio']

        if health_ratio < threshold_config.emergency_threshold:
            level = AlertLevel.EMERGENCY
        elif health_ratio < threshold_config.critical_threshold:
            level = AlertLevel.CRITICAL
        elif health_ratio < threshold_config.warning_threshold:
            level = AlertLevel.WARNING
        else:
            level = None

        if level:
            self._create_alert(
                level,
                'health_ratio',
                f"Manager health ratio below threshold: {health_ratio:.2f}",
                {
                    'health_ratio': health_ratio,
                    'healthy_managers': metrics.healthy_managers,
                    'total_managers': metrics.total_managers,
                    'threshold_config': threshold_config.name
                }
            )

    def _check_threshold(self, threshold_name: str, value: float, details: Dict[str, Any]):
        """Check a specific threshold and generate alert if needed"""
        threshold_config = self.thresholds.get(threshold_name)
        if not threshold_config or not threshold_config.enabled:
            return

        # Determine alert level
        if value >= threshold_config.emergency_threshold:
            level = AlertLevel.EMERGENCY
        elif value >= threshold_config.critical_threshold:
            level = AlertLevel.CRITICAL
        elif value >= threshold_config.warning_threshold:
            level = AlertLevel.WARNING
        else:
            return  # No alert needed

        # Create alert
        message = f"{threshold_name} threshold exceeded: {value} >= {threshold_config.warning_threshold}"
        self._create_alert(level, threshold_name, message, details)

    def _create_alert(self, level: AlertLevel, category: str, message: str, details: Dict[str, Any]):
        """Create and process a new alert"""
        alert = Alert(
            level=level,
            category=category,
            message=message,
            details=details
        )

        # Check for duplicate recent alerts
        if self._is_duplicate_alert(alert):
            return

        # Add to active alerts
        with self._metrics_lock:
            self.active_alerts.append(alert)

        # Log the alert
        log_level = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.CRITICAL: logger.error,
            AlertLevel.EMERGENCY: logger.critical
        }.get(level, logger.info)

        log_level(f"ALERT [{level.value.upper()}] {category}: {message}")

        # Notify alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler {handler.__name__}: {e}")

        # Auto-trigger emergency response for emergency alerts
        if level == AlertLevel.EMERGENCY:
            self._trigger_emergency_response(alert)

    def _is_duplicate_alert(self, new_alert: Alert) -> bool:
        """Check if this alert is a duplicate of a recent alert"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)  # 5-minute deduplication window

        for alert in self.active_alerts:
            if (alert.category == new_alert.category and
                alert.level == new_alert.level and
                alert.timestamp > cutoff_time and
                not alert.resolved):
                return True

        return False

    def _trigger_emergency_response(self, alert: Alert):
        """Trigger emergency response for critical alerts"""
        try:
            logger.critical(f"EMERGENCY RESPONSE TRIGGERED: {alert.category} - {alert.message}")

            if self.factory and alert.category in ['managers_per_user', 'zombie_ratio']:
                # Try emergency cleanup
                user_ids = list(alert.details.get('managers_by_user', {}).keys()) if 'managers_by_user' in alert.details else []

                for user_id in user_ids[:5]:  # Limit to 5 users to prevent overload
                    try:
                        # Import cleanup level enum
                        from netra_backend.app.websocket_core.websocket_manager_factory import CleanupLevel
                        asyncio.run(self.factory._emergency_cleanup_user_managers(user_id, CleanupLevel.AGGRESSIVE))
                        logger.info(f"Emergency cleanup executed for user {user_id}")
                    except Exception as e:
                        logger.error(f"Emergency cleanup failed for user {user_id}: {e}")

        except Exception as e:
            logger.error(f"Emergency response failed: {e}")

    def _cleanup_old_data(self):
        """Clean up old metrics and resolved alerts"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)  # Keep 24 hours of data

            with self._metrics_lock:
                # Clean old metrics (keep last 100 entries or 24 hours, whichever is more recent)
                if len(self.metrics_history) > 100:
                    self.metrics_history = [m for m in self.metrics_history if m.timestamp > cutoff_time]
                    if len(self.metrics_history) < 50:  # Keep at least 50 entries
                        self.metrics_history = self.metrics_history[-50:]

                # Move old resolved alerts to archive
                old_resolved = [a for a in self.resolved_alerts if a.timestamp < cutoff_time]
                self.resolved_alerts = [a for a in self.resolved_alerts if a.timestamp >= cutoff_time]

                # Auto-resolve old active alerts
                for alert in self.active_alerts[:]:
                    if alert.age_seconds() > 3600:  # 1 hour old
                        alert.resolve()
                        self.active_alerts.remove(alert)
                        self.resolved_alerts.append(alert)

        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive data for monitoring dashboard"""
        with self._metrics_lock:
            current = self.current_metrics

            # Recent metrics (last hour)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_metrics = [m for m in self.metrics_history if m.timestamp > recent_cutoff]

            # Active alerts by level
            alerts_by_level = {}
            for level in AlertLevel:
                alerts_by_level[level.value] = [
                    {
                        'category': a.category,
                        'message': a.message,
                        'timestamp': a.timestamp.isoformat(),
                        'age_seconds': a.age_seconds(),
                        'details': a.details
                    }
                    for a in self.active_alerts if a.level == level and not a.resolved
                ]

            return {
                'monitor_status': {
                    'state': self.state.value,
                    'monitoring_interval': self.monitoring_interval,
                    'uptime_seconds': time.time() - (self._monitor_thread.ident if self._monitor_thread else time.time())
                },
                'current_metrics': {
                    'timestamp': current.timestamp.isoformat(),
                    'total_managers': current.total_managers,
                    'total_users': current.total_users,
                    'peak_managers_per_user': current.peak_managers_per_user,
                    'health_ratio': current.health_ratio(),
                    'zombie_ratio': current.zombie_ratio(),
                    'healthy_managers': current.healthy_managers,
                    'zombie_managers': current.zombie_managers,
                    'inactive_managers': current.inactive_managers,
                    'cleanup_events_total': current.cleanup_events_total,
                    'emergency_cleanups_total': current.emergency_cleanups_total
                },
                'alerts': {
                    'active_count': len([a for a in self.active_alerts if not a.resolved]),
                    'by_level': alerts_by_level
                },
                'thresholds': {
                    name: {
                        'warning': config.warning_threshold,
                        'critical': config.critical_threshold,
                        'emergency': config.emergency_threshold,
                        'enabled': config.enabled
                    }
                    for name, config in self.thresholds.items()
                },
                'trends': {
                    'manager_count_trend': [
                        {'timestamp': m.timestamp.isoformat(), 'value': m.total_managers}
                        for m in recent_metrics[-20:]  # Last 20 data points
                    ],
                    'health_ratio_trend': [
                        {'timestamp': m.timestamp.isoformat(), 'value': m.health_ratio()}
                        for m in recent_metrics[-20:]
                    ]
                }
            }

    def get_health_summary(self) -> Dict[str, Any]:
        """Get simple health summary for status checks"""
        with self._metrics_lock:
            current = self.current_metrics
            active_alerts = [a for a in self.active_alerts if not a.resolved]

            # Determine overall health
            emergency_alerts = [a for a in active_alerts if a.level == AlertLevel.EMERGENCY]
            critical_alerts = [a for a in active_alerts if a.level == AlertLevel.CRITICAL]

            if emergency_alerts:
                overall_status = "EMERGENCY"
            elif critical_alerts:
                overall_status = "CRITICAL"
            elif len(active_alerts) > 5:
                overall_status = "WARNING"
            else:
                overall_status = "HEALTHY"

            return {
                'overall_status': overall_status,
                'total_managers': current.total_managers,
                'health_ratio': current.health_ratio(),
                'zombie_ratio': current.zombie_ratio(),
                'active_alerts': len(active_alerts),
                'peak_managers_per_user': current.peak_managers_per_user,
                'last_update': current.timestamp.isoformat()
            }


# Global monitor instance
_global_monitor: Optional[WebSocketFactoryMonitor] = None
_monitor_lock = threading.Lock()


def get_websocket_factory_monitor() -> WebSocketFactoryMonitor:
    """Get global factory monitor instance"""
    global _global_monitor

    with _monitor_lock:
        if _global_monitor is None:
            # Try to get factory instance
            try:
                from netra_backend.app.websocket_core.websocket_manager_factory import get_websocket_manager_factory
                factory = get_websocket_manager_factory()
            except Exception as e:
                logger.warning(f"Could not get factory for monitoring: {e}")
                factory = None

            _global_monitor = WebSocketFactoryMonitor(factory=factory)
            logger.info("Global WebSocketFactoryMonitor instance created")

        return _global_monitor


def start_global_monitoring():
    """Start global factory monitoring"""
    monitor = get_websocket_factory_monitor()
    monitor.start_monitoring()


def stop_global_monitoring():
    """Stop global factory monitoring"""
    global _global_monitor

    with _monitor_lock:
        if _global_monitor:
            _global_monitor.stop_monitoring()


def get_monitoring_health_endpoint() -> Dict[str, Any]:
    """Health endpoint for monitoring integration"""
    try:
        monitor = get_websocket_factory_monitor()
        return monitor.get_health_summary()
    except Exception as e:
        return {
            'overall_status': 'ERROR',
            'error': str(e),
            'last_update': datetime.now(timezone.utc).isoformat()
        }


# Export public interface
__all__ = [
    'WebSocketFactoryMonitor',
    'AlertLevel',
    'MonitoringState',
    'Alert',
    'MonitoringMetrics',
    'AlertThreshold',
    'get_websocket_factory_monitor',
    'start_global_monitoring',
    'stop_global_monitoring',
    'get_monitoring_health_endpoint'
]