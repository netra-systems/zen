"""VPC Connector Load Monitoring Module - P0 Emergency Infrastructure Monitoring

This module provides monitoring and alerting for VPC connector capacity and load
to prevent and detect capacity exhaustion emergencies.

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure (ALL users impacted by VPC failures)
- Business Goal: Proactive infrastructure monitoring and emergency prevention
- Value Impact: Early warning system prevents complete service outages
- Strategic Impact: Protects $500K+ ARR by maintaining service availability

P0 EMERGENCY CONTEXT:
- VPC connector capacity exhaustion causes cascading failures
- Database and WebSocket connections consume VPC connector capacity
- Need real-time monitoring of VPC load and early warning alerts
- Automated emergency mode activation based on load thresholds

MONITORING APPROACH:
1. Track database connection pool utilization
2. Monitor WebSocket connection counts
3. Calculate estimated VPC connector load
4. Provide early warning alerts at threshold levels
5. Automatically trigger emergency mode when necessary
6. Generate actionable recommendations for infrastructure team
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import json

logger = logging.getLogger(__name__)


class VPCLoadLevel(Enum):
    """VPC connector load levels for monitoring."""
    NORMAL = "normal"          # < 60% capacity
    ELEVATED = "elevated"      # 60-75% capacity
    HIGH = "high"             # 75-90% capacity
    CRITICAL = "critical"     # 90-95% capacity
    EMERGENCY = "emergency"   # > 95% capacity


@dataclass
class VPCConnectionSource:
    """Source of VPC connector connections."""
    source_type: str  # e.g., "database", "websocket", "external_api"
    service_name: str
    current_connections: int
    max_connections: int
    connection_rate: float  # connections per second
    last_updated: datetime = field(default_factory=lambda: datetime.now())


@dataclass
class VPCLoadMetrics:
    """VPC connector load metrics."""
    total_estimated_connections: int = 0
    estimated_capacity_usage_percent: float = 0.0
    database_connections: int = 0
    websocket_connections: int = 0
    external_api_connections: int = 0
    connection_sources: Dict[str, VPCConnectionSource] = field(default_factory=dict)
    last_measurement: datetime = field(default_factory=lambda: datetime.now())
    load_level: VPCLoadLevel = VPCLoadLevel.NORMAL

    # Historical tracking
    load_history: List[Dict[str, Any]] = field(default_factory=list)
    alert_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class VPCAlert:
    """VPC connector capacity alert."""
    alert_id: str
    level: VPCLoadLevel
    message: str
    current_usage_percent: float
    estimated_connections: int
    recommendations: List[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    acknowledged: bool = False


class VPCConnectorMonitor:
    """Monitor for VPC connector capacity and load."""

    def __init__(self, estimated_vpc_capacity: int = 3000):
        """Initialize VPC connector monitor.

        Args:
            estimated_vpc_capacity: Estimated total VPC connector capacity
        """
        self.estimated_vpc_capacity = estimated_vpc_capacity
        self.metrics = VPCLoadMetrics()
        self.active_alerts: Dict[str, VPCAlert] = {}
        self.alert_callbacks: List[Callable[[VPCAlert], None]] = []
        self._monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None

        # Load thresholds for different levels
        self.load_thresholds = {
            VPCLoadLevel.ELEVATED: 60.0,
            VPCLoadLevel.HIGH: 75.0,
            VPCLoadLevel.CRITICAL: 90.0,
            VPCLoadLevel.EMERGENCY: 95.0
        }

        # Emergency mode auto-activation
        self.emergency_activation_threshold = 90.0  # Auto-activate emergency mode at 90%
        self.emergency_mode_activated = False

        logger.info(f"🔍 VPC Connector Monitor initialized (estimated capacity: {estimated_vpc_capacity})")

    async def start_monitoring(self, interval_seconds: int = 30):
        """Start continuous VPC load monitoring.

        Args:
            interval_seconds: Monitoring interval in seconds
        """
        if self._monitoring_active:
            logger.warning("VPC monitoring already active")
            return

        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop(interval_seconds))
        logger.info(f"📊 VPC connector monitoring started (interval: {interval_seconds}s)")

    async def stop_monitoring(self):
        """Stop VPC load monitoring."""
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("📊 VPC connector monitoring stopped")

    async def _monitoring_loop(self, interval_seconds: int):
        """Main monitoring loop."""
        while self._monitoring_active:
            try:
                await self.update_vpc_load_metrics()
                await self._check_alert_conditions()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in VPC monitoring loop: {e}")
                await asyncio.sleep(interval_seconds)

    async def update_vpc_load_metrics(self):
        """Update VPC load metrics by collecting data from various sources."""
        try:
            # Collect database connection metrics
            await self._collect_database_metrics()

            # Collect WebSocket connection metrics
            await self._collect_websocket_metrics()

            # Collect other connection sources
            await self._collect_external_metrics()

            # Calculate total estimated connections
            total_connections = sum(
                source.current_connections
                for source in self.metrics.connection_sources.values()
            )

            self.metrics.total_estimated_connections = total_connections
            self.metrics.estimated_capacity_usage_percent = (total_connections / self.estimated_vpc_capacity) * 100
            self.metrics.last_measurement = datetime.now()

            # Determine load level
            old_level = self.metrics.load_level
            self.metrics.load_level = self._calculate_load_level(self.metrics.estimated_capacity_usage_percent)

            # Log significant load changes
            if self.metrics.load_level != old_level:
                logger.info(f"🔄 VPC load level changed: {old_level.value} → {self.metrics.load_level.value} "
                           f"({self.metrics.estimated_capacity_usage_percent:.1f}% capacity)")

            # Add to history (keep last 100 measurements)
            self.metrics.load_history.append({
                "timestamp": self.metrics.last_measurement.isoformat(),
                "usage_percent": self.metrics.estimated_capacity_usage_percent,
                "total_connections": total_connections,
                "load_level": self.metrics.load_level.value
            })
            if len(self.metrics.load_history) > 100:
                self.metrics.load_history.pop(0)

        except Exception as e:
            logger.error(f"Failed to update VPC load metrics: {e}")

    async def _collect_database_metrics(self):
        """Collect database connection pool metrics."""
        try:
            from netra_backend.app.db.database_manager import get_database_manager
            db_manager = get_database_manager()

            if hasattr(db_manager, 'get_pool_stats'):
                pool_stats = db_manager.get_pool_stats()
                current_connections = pool_stats.get('active_sessions_count', 0)

                pool_config = pool_stats.get('pool_configuration', {})
                max_connections = pool_config.get('total_capacity', 75)  # pool_size + max_overflow

                self.metrics.database_connections = current_connections
                self.metrics.connection_sources['database_primary'] = VPCConnectionSource(
                    source_type="database",
                    service_name="postgresql_primary",
                    current_connections=current_connections,
                    max_connections=max_connections,
                    connection_rate=0.0  # TODO: Calculate from historical data
                )

        except Exception as e:
            logger.warning(f"Failed to collect database metrics: {e}")

    async def _collect_websocket_metrics(self):
        """Collect WebSocket connection metrics."""
        try:
            from netra_backend.app.websocket_core.emergency_throttling import get_websocket_throttling_metrics
            ws_metrics = get_websocket_throttling_metrics()

            current_connections = ws_metrics.get('connections', {}).get('total', 0)
            max_connections = ws_metrics.get('limits', {}).get('max_total_connections', 1000)

            self.metrics.websocket_connections = current_connections
            self.metrics.connection_sources['websocket'] = VPCConnectionSource(
                source_type="websocket",
                service_name="websocket_manager",
                current_connections=current_connections,
                max_connections=max_connections,
                connection_rate=0.0  # TODO: Calculate from historical data
            )

        except Exception as e:
            logger.warning(f"Failed to collect WebSocket metrics: {e}")

    async def _collect_external_metrics(self):
        """Collect metrics from external API connections."""
        try:
            # TODO: Collect metrics from external API connections (LLM providers, etc.)
            # For now, estimate based on typical usage
            estimated_external = 10  # Conservative estimate

            self.metrics.external_api_connections = estimated_external
            self.metrics.connection_sources['external_apis'] = VPCConnectionSource(
                source_type="external_api",
                service_name="llm_providers",
                current_connections=estimated_external,
                max_connections=50,
                connection_rate=0.0
            )

        except Exception as e:
            logger.warning(f"Failed to collect external API metrics: {e}")

    def _calculate_load_level(self, usage_percent: float) -> VPCLoadLevel:
        """Calculate VPC load level based on usage percentage."""
        if usage_percent >= self.load_thresholds[VPCLoadLevel.EMERGENCY]:
            return VPCLoadLevel.EMERGENCY
        elif usage_percent >= self.load_thresholds[VPCLoadLevel.CRITICAL]:
            return VPCLoadLevel.CRITICAL
        elif usage_percent >= self.load_thresholds[VPCLoadLevel.HIGH]:
            return VPCLoadLevel.HIGH
        elif usage_percent >= self.load_thresholds[VPCLoadLevel.ELEVATED]:
            return VPCLoadLevel.ELEVATED
        else:
            return VPCLoadLevel.NORMAL

    async def _check_alert_conditions(self):
        """Check if any alert conditions are met."""
        current_usage = self.metrics.estimated_capacity_usage_percent
        current_level = self.metrics.load_level

        # Check for emergency mode auto-activation
        if (current_usage >= self.emergency_activation_threshold and
            not self.emergency_mode_activated):
            await self._activate_emergency_mode()

        # Generate alerts for high load levels
        if current_level in [VPCLoadLevel.HIGH, VPCLoadLevel.CRITICAL, VPCLoadLevel.EMERGENCY]:
            alert_id = f"vpc_load_{current_level.value}_{int(time.time())}"

            # Check if we already have a recent alert for this level
            recent_alert_exists = any(
                alert.level == current_level and
                (datetime.now() - alert.timestamp).total_seconds() < 300  # 5 minutes
                for alert in self.active_alerts.values()
            )

            if not recent_alert_exists:
                alert = self._create_alert(alert_id, current_level, current_usage)
                self.active_alerts[alert_id] = alert
                await self._send_alert(alert)

    async def _activate_emergency_mode(self):
        """Automatically activate emergency mode due to high VPC load."""
        try:
            from netra_backend.app.core.configuration.emergency import get_emergency_config, EmergencyLevel
            emergency_config = get_emergency_config()

            # Determine emergency level based on load
            if self.metrics.estimated_capacity_usage_percent >= 95:
                emergency_level = EmergencyLevel.CRITICAL
            elif self.metrics.estimated_capacity_usage_percent >= 90:
                emergency_level = EmergencyLevel.HIGH
            else:
                emergency_level = EmergencyLevel.ELEVATED

            emergency_config.set_emergency_level(emergency_level)
            self.emergency_mode_activated = True

            logger.critical(f"🚨 AUTO-ACTIVATED EMERGENCY MODE: {emergency_level.value.upper()} due to VPC load "
                           f"({self.metrics.estimated_capacity_usage_percent:.1f}%)")

            # Create emergency activation alert
            alert_id = f"emergency_auto_activation_{int(time.time())}"
            alert = VPCAlert(
                alert_id=alert_id,
                level=VPCLoadLevel.EMERGENCY,
                message=f"Emergency mode automatically activated due to VPC connector load ({self.metrics.estimated_capacity_usage_percent:.1f}%)",
                current_usage_percent=self.metrics.estimated_capacity_usage_percent,
                estimated_connections=self.metrics.total_estimated_connections,
                recommendations=[
                    "Emergency mode has been automatically activated",
                    "Database connection pools have been reduced",
                    "WebSocket connection throttling is now active",
                    "Infrastructure team should scale VPC connector capacity immediately",
                    f"Current load: {self.metrics.total_estimated_connections}/{self.estimated_vpc_capacity} connections"
                ]
            )

            self.active_alerts[alert_id] = alert
            await self._send_alert(alert)

        except Exception as e:
            logger.error(f"Failed to activate emergency mode: {e}")

    def _create_alert(self, alert_id: str, level: VPCLoadLevel, usage_percent: float) -> VPCAlert:
        """Create a VPC load alert."""
        recommendations = self._get_recommendations_for_level(level, usage_percent)

        if level == VPCLoadLevel.EMERGENCY:
            message = f"EMERGENCY: VPC connector capacity critically high ({usage_percent:.1f}%)"
        elif level == VPCLoadLevel.CRITICAL:
            message = f"CRITICAL: VPC connector capacity dangerously high ({usage_percent:.1f}%)"
        elif level == VPCLoadLevel.HIGH:
            message = f"HIGH: VPC connector capacity elevated ({usage_percent:.1f}%)"
        else:
            message = f"{level.value.upper()}: VPC connector load increased ({usage_percent:.1f}%)"

        return VPCAlert(
            alert_id=alert_id,
            level=level,
            message=message,
            current_usage_percent=usage_percent,
            estimated_connections=self.metrics.total_estimated_connections,
            recommendations=recommendations
        )

    def _get_recommendations_for_level(self, level: VPCLoadLevel, usage_percent: float) -> List[str]:
        """Get recommendations based on load level."""
        recommendations = []

        if level == VPCLoadLevel.EMERGENCY:
            recommendations.extend([
                "IMMEDIATE ACTION REQUIRED: Scale VPC connector capacity",
                "Consider emergency service degradation to reduce load",
                "Monitor for service outages and connection failures",
                "Activate incident response procedures"
            ])
        elif level == VPCLoadLevel.CRITICAL:
            recommendations.extend([
                "Scale VPC connector capacity immediately",
                "Activate emergency configuration to reduce connection load",
                "Monitor service health closely",
                "Prepare for potential service degradation"
            ])
        elif level == VPCLoadLevel.HIGH:
            recommendations.extend([
                "Plan VPC connector capacity scaling",
                "Review connection pool configurations",
                "Monitor connection growth trends",
                "Consider enabling connection throttling"
            ])
        else:
            recommendations.extend([
                "Monitor VPC connector load trends",
                "Review connection patterns for optimization opportunities",
                "Ensure auto-scaling is properly configured"
            ])

        # Add specific source recommendations
        db_connections = self.metrics.database_connections
        ws_connections = self.metrics.websocket_connections

        if db_connections > 50:
            recommendations.append(f"High database connections ({db_connections}) - review pool configuration")

        if ws_connections > 200:
            recommendations.append(f"High WebSocket connections ({ws_connections}) - consider throttling")

        return recommendations

    async def _send_alert(self, alert: VPCAlert):
        """Send alert to registered callbacks."""
        # Add to alert history
        self.metrics.alert_history.append({
            "alert_id": alert.alert_id,
            "level": alert.level.value,
            "message": alert.message,
            "usage_percent": alert.current_usage_percent,
            "timestamp": alert.timestamp.isoformat()
        })

        # Keep only last 50 alerts in history
        if len(self.metrics.alert_history) > 50:
            self.metrics.alert_history.pop(0)

        # Log the alert
        if alert.level == VPCLoadLevel.EMERGENCY:
            logger.critical(f"🚨 VPC EMERGENCY ALERT: {alert.message}")
        elif alert.level == VPCLoadLevel.CRITICAL:
            logger.critical(f"⚠️ VPC CRITICAL ALERT: {alert.message}")
        else:
            logger.warning(f"📊 VPC LOAD ALERT: {alert.message}")

        for recommendation in alert.recommendations:
            logger.info(f"   💡 {recommendation}")

        # Call registered callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    def register_alert_callback(self, callback: Callable[[VPCAlert], None]):
        """Register a callback for VPC alerts."""
        if callback not in self.alert_callbacks:
            self.alert_callbacks.append(callback)
            logger.debug(f"Registered VPC alert callback: {callback.__name__}")

    def get_current_status(self) -> Dict[str, Any]:
        """Get current VPC connector status."""
        return {
            "load_level": self.metrics.load_level.value,
            "usage_percent": self.metrics.estimated_capacity_usage_percent,
            "total_connections": self.metrics.total_estimated_connections,
            "estimated_capacity": self.estimated_vpc_capacity,
            "emergency_mode_active": self.emergency_mode_activated,
            "connection_breakdown": {
                "database": self.metrics.database_connections,
                "websocket": self.metrics.websocket_connections,
                "external_apis": self.metrics.external_api_connections
            },
            "active_alerts": len(self.active_alerts),
            "last_measurement": self.metrics.last_measurement.isoformat() if self.metrics.last_measurement else None
        }

    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed VPC connector metrics."""
        return {
            "current_status": self.get_current_status(),
            "connection_sources": {
                name: {
                    "type": source.source_type,
                    "service": source.service_name,
                    "current": source.current_connections,
                    "max": source.max_connections,
                    "utilization_percent": (source.current_connections / source.max_connections * 100) if source.max_connections > 0 else 0,
                    "last_updated": source.last_updated.isoformat()
                }
                for name, source in self.metrics.connection_sources.items()
            },
            "load_history": self.metrics.load_history[-20:],  # Last 20 measurements
            "active_alerts": {
                alert_id: {
                    "level": alert.level.value,
                    "message": alert.message,
                    "usage_percent": alert.current_usage_percent,
                    "timestamp": alert.timestamp.isoformat(),
                    "acknowledged": alert.acknowledged
                }
                for alert_id, alert in self.active_alerts.items()
            },
            "alert_history": self.metrics.alert_history[-10:],  # Last 10 alerts
            "thresholds": {level.value: threshold for level, threshold in self.load_thresholds.items()},
            "emergency_activation_threshold": self.emergency_activation_threshold
        }

    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an active alert."""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            logger.info(f"📋 VPC alert acknowledged: {alert_id}")
            return True
        return False

    async def clear_acknowledged_alerts(self):
        """Clear all acknowledged alerts."""
        acknowledged_alerts = [
            alert_id for alert_id, alert in self.active_alerts.items()
            if alert.acknowledged
        ]

        for alert_id in acknowledged_alerts:
            del self.active_alerts[alert_id]

        if acknowledged_alerts:
            logger.info(f"🧹 Cleared {len(acknowledged_alerts)} acknowledged VPC alerts")


# Global VPC monitor instance
_vpc_monitor: Optional[VPCConnectorMonitor] = None


def get_vpc_monitor() -> VPCConnectorMonitor:
    """Get the global VPC connector monitor instance."""
    global _vpc_monitor
    if _vpc_monitor is None:
        _vpc_monitor = VPCConnectorMonitor()
    return _vpc_monitor


async def start_vpc_monitoring(interval_seconds: int = 30):
    """Start VPC connector monitoring."""
    await get_vpc_monitor().start_monitoring(interval_seconds)


async def stop_vpc_monitoring():
    """Stop VPC connector monitoring."""
    await get_vpc_monitor().stop_monitoring()


def get_vpc_status() -> Dict[str, Any]:
    """Get current VPC connector status."""
    return get_vpc_monitor().get_current_status()


def get_vpc_detailed_metrics() -> Dict[str, Any]:
    """Get detailed VPC connector metrics."""
    return get_vpc_monitor().get_detailed_metrics()


# Export public interface
__all__ = [
    'VPCLoadLevel',
    'VPCAlert',
    'VPCConnectorMonitor',
    'get_vpc_monitor',
    'start_vpc_monitoring',
    'stop_vpc_monitoring',
    'get_vpc_status',
    'get_vpc_detailed_metrics'
]