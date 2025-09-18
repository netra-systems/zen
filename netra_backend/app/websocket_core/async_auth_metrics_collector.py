"""
Async Authentication Metrics Collector - Real-time Monitoring

Business Value Justification (BVJ):
- Segment: Platform/Internal - Authentication Infrastructure
- Business Goal: Provide real-time authentication monitoring and alerting
- Value Impact: Enable proactive detection of authentication issues before they impact users
- Revenue Impact: Protect $500K+ ARR chat functionality through early issue detection

This module implements an asynchronous metrics collector for Issue #1300 Task #2,
providing real-time aggregation and monitoring of WebSocket authentication metrics.

Key Features:
1. Async background collection of authentication metrics
2. Real-time aggregation and statistical analysis
3. Configurable collection intervals and batch processing
4. Integration with existing monitoring infrastructure
5. Memory-efficient storage with configurable retention policies
6. Health monitoring of the collector itself
7. Export capabilities for monitoring dashboards
"""

import asyncio
import time
import json
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import defaultdict, deque
import threading
import logging

from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.websocket_core.auth_monitoring import (
    get_websocket_auth_monitor,
    AuthEventType,
    get_auth_monitoring_metrics,
    get_auth_monitoring_health
)
from netra_backend.app.monitoring.websocket_metrics import get_websocket_metrics_collector

logger = get_logger(__name__)


@dataclass
class CollectionConfig:
    """Configuration for the async metrics collector."""
    collection_interval_seconds: float = 5.0  # How often to collect metrics
    aggregation_interval_seconds: float = 30.0  # How often to aggregate data
    retention_hours: int = 24  # How long to keep historical data
    max_events_per_batch: int = 1000  # Max events to process in one batch
    health_check_interval_seconds: float = 60.0  # Health check frequency
    export_interval_seconds: float = 300.0  # How often to export metrics (5 minutes)
    alert_check_interval_seconds: float = 10.0  # How often to check for alerts
    
    # Alert thresholds
    alert_failure_rate_threshold: float = 20.0  # Alert if >20% failures
    alert_latency_threshold_ms: float = 2000.0  # Alert if latency >2 seconds
    alert_connection_failure_threshold: float = 25.0  # Alert if >25% connection failures


@dataclass
class MetricSnapshot:
    """A snapshot of metrics at a specific point in time."""
    timestamp: datetime
    auth_attempts: int = 0
    auth_successes: int = 0
    auth_failures: int = 0
    auth_success_rate: float = 100.0
    token_validations: int = 0
    token_validation_successes: int = 0
    token_validation_failures: int = 0
    session_creations: int = 0
    session_invalidations: int = 0
    connection_upgrades: int = 0
    connection_upgrade_successes: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    active_sessions: int = 0
    active_connections: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/export."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "auth_attempts": self.auth_attempts,
            "auth_successes": self.auth_successes,
            "auth_failures": self.auth_failures,
            "auth_success_rate": round(self.auth_success_rate, 2),
            "token_validations": self.token_validations,
            "token_validation_successes": self.token_validation_successes,
            "token_validation_failures": self.token_validation_failures,
            "session_creations": self.session_creations,
            "session_invalidations": self.session_invalidations,
            "connection_upgrades": self.connection_upgrades,
            "connection_upgrade_successes": self.connection_upgrade_successes,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "active_sessions": self.active_sessions,
            "active_connections": self.active_connections
        }


@dataclass
class AggregatedMetrics:
    """Aggregated metrics over a time period."""
    start_time: datetime
    end_time: datetime
    total_auth_attempts: int = 0
    total_auth_successes: int = 0
    total_auth_failures: int = 0
    avg_success_rate: float = 100.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    total_session_creations: int = 0
    total_connection_upgrades: int = 0
    peak_active_sessions: int = 0
    peak_active_connections: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/export."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
            "total_auth_attempts": self.total_auth_attempts,
            "total_auth_successes": self.total_auth_successes,
            "total_auth_failures": self.total_auth_failures,
            "avg_success_rate": round(self.avg_success_rate, 2),
            "min_latency_ms": round(self.min_latency_ms, 2),
            "max_latency_ms": round(self.max_latency_ms, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "total_session_creations": self.total_session_creations,
            "total_connection_upgrades": self.total_connection_upgrades,
            "peak_active_sessions": self.peak_active_sessions,
            "peak_active_connections": self.peak_active_connections
        }


class CollectorStatus(Enum):
    """Status of the metrics collector."""
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class AsyncAuthMetricsCollector:
    """
    Async Authentication Metrics Collector for Issue #1300 Task #2.
    
    Provides real-time collection, aggregation, and monitoring of WebSocket
    authentication metrics with configurable intervals and retention policies.
    
    Features:
    - Background collection of authentication metrics
    - Real-time aggregation and statistical analysis
    - Configurable collection and retention policies
    - Health monitoring and self-diagnostics
    - Export capabilities for dashboards
    - Alert generation for anomalies
    """
    
    def __init__(self, config: Optional[CollectionConfig] = None):
        """
        Initialize the async metrics collector.
        
        Args:
            config: Optional configuration, defaults to CollectionConfig()
        """
        self.config = config or CollectionConfig()
        self._lock = threading.RLock()
        
        # Collection state
        self._status = CollectorStatus.STOPPED
        self._collection_task: Optional[asyncio.Task] = None
        self._aggregation_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._alert_check_task: Optional[asyncio.Task] = None
        
        # Metrics storage
        self._metric_snapshots: deque = deque(maxlen=self._calculate_max_snapshots())
        self._aggregated_metrics: deque = deque(maxlen=self._calculate_max_aggregations())
        
        # Health tracking
        self._collector_start_time = datetime.now(timezone.utc)
        self._last_collection_time = None
        self._last_aggregation_time = None
        self._collection_errors = 0
        self._aggregation_errors = 0
        
        # Statistics
        self._total_collections = 0
        self._total_aggregations = 0
        self._total_exports = 0
        
        # Alert tracking
        self._alerts_generated = 0
        self._last_alert_time = None
        self._alert_suppression: Dict[str, datetime] = {}  # Alert type -> last alert time
        
        # Integration components
        self._auth_monitor = None
        self._websocket_metrics = None
        
        logger.info(f"AsyncAuthMetricsCollector initialized with config: collection_interval={self.config.collection_interval_seconds}s")
    
    async def start(self) -> None:
        """Start the async metrics collector."""
        try:
            if self._status == CollectorStatus.RUNNING:
                logger.warning("Metrics collector is already running")
                return
            
            self._status = CollectorStatus.STARTING
            logger.info("Starting AsyncAuthMetricsCollector...")
            
            # Initialize integration components
            try:
                self._auth_monitor = get_websocket_auth_monitor()
                self._websocket_metrics = get_websocket_metrics_collector()
                logger.info("Integration components initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize some integration components: {e}")
            
            # Start background tasks
            self._collection_task = asyncio.create_task(self._collection_loop())
            self._aggregation_task = asyncio.create_task(self._aggregation_loop())
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            self._alert_check_task = asyncio.create_task(self._alert_check_loop())
            
            self._status = CollectorStatus.RUNNING
            logger.info("AsyncAuthMetricsCollector started successfully")
            
        except Exception as e:
            self._status = CollectorStatus.ERROR
            logger.error(f"Failed to start metrics collector: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the async metrics collector."""
        try:
            if self._status == CollectorStatus.STOPPED:
                logger.warning("Metrics collector is already stopped")
                return
                
            self._status = CollectorStatus.STOPPING
            logger.info("Stopping AsyncAuthMetricsCollector...")
            
            # Cancel background tasks
            tasks = [
                self._collection_task,
                self._aggregation_task,
                self._health_check_task,
                self._alert_check_task
            ]
            
            for task in tasks:
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.warning(f"Error stopping task: {e}")
            
            self._status = CollectorStatus.STOPPED
            logger.info("AsyncAuthMetricsCollector stopped")
            
        except Exception as e:
            self._status = CollectorStatus.ERROR
            logger.error(f"Error stopping metrics collector: {e}")
    
    async def pause(self) -> None:
        """Pause metrics collection (keeps tasks running but skips collection)."""
        self._status = CollectorStatus.PAUSED
        logger.info("AsyncAuthMetricsCollector paused")
    
    async def resume(self) -> None:
        """Resume metrics collection."""
        if self._status == CollectorStatus.PAUSED:
            self._status = CollectorStatus.RUNNING
            logger.info("AsyncAuthMetricsCollector resumed")
    
    def get_status(self) -> Dict[str, Any]:
        """Get collector status and statistics."""
        with self._lock:
            uptime_seconds = (datetime.now(timezone.utc) - self._collector_start_time).total_seconds()
            
            return {
                "status": self._status.value,
                "uptime_seconds": uptime_seconds,
                "config": asdict(self.config),
                "statistics": {
                    "total_collections": self._total_collections,
                    "total_aggregations": self._total_aggregations,
                    "total_exports": self._total_exports,
                    "collection_errors": self._collection_errors,
                    "aggregation_errors": self._aggregation_errors,
                    "alerts_generated": self._alerts_generated
                },
                "timestamps": {
                    "collector_start_time": self._collector_start_time.isoformat(),
                    "last_collection_time": self._last_collection_time.isoformat() if self._last_collection_time else None,
                    "last_aggregation_time": self._last_aggregation_time.isoformat() if self._last_aggregation_time else None,
                    "last_alert_time": self._last_alert_time.isoformat() if self._last_alert_time else None
                },
                "storage": {
                    "metric_snapshots_count": len(self._metric_snapshots),
                    "aggregated_metrics_count": len(self._aggregated_metrics),
                    "max_snapshots": self._metric_snapshots.maxlen,
                    "max_aggregations": self._aggregated_metrics.maxlen
                },
                "tasks": {
                    "collection_task_running": self._collection_task and not self._collection_task.done(),
                    "aggregation_task_running": self._aggregation_task and not self._aggregation_task.done(),
                    "health_check_task_running": self._health_check_task and not self._health_check_task.done(),
                    "alert_check_task_running": self._alert_check_task and not self._alert_check_task.done()
                }
            }
    
    def get_recent_snapshots(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent metric snapshots."""
        with self._lock:
            snapshots = list(self._metric_snapshots)
            # Return most recent first
            snapshots.reverse()
            return [snapshot.to_dict() for snapshot in snapshots[:limit]]
    
    def get_aggregated_metrics(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get aggregated metrics for the specified time period."""
        with self._lock:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            relevant_metrics = [
                agg for agg in self._aggregated_metrics
                if agg.end_time >= cutoff_time
            ]
            
            # Return most recent first
            relevant_metrics.reverse()
            return [metrics.to_dict() for metrics in relevant_metrics]
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current real-time metrics."""
        try:
            # Get metrics from auth monitor
            global_metrics = get_auth_monitoring_metrics()
            
            # Get latest snapshot if available
            latest_snapshot = None
            with self._lock:
                if self._metric_snapshots:
                    latest_snapshot = self._metric_snapshots[-1].to_dict()
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "global_metrics": global_metrics,
                "latest_snapshot": latest_snapshot,
                "collector_status": self._status.value
            }
            
        except Exception as e:
            logger.error(f"Error getting current metrics: {e}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "collector_status": self._status.value
            }
    
    async def export_metrics(self, format_type: str = "json") -> Dict[str, Any]:
        """Export metrics for external monitoring systems."""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Get all available data
            status = self.get_status()
            recent_snapshots = self.get_recent_snapshots(100)
            aggregated_data = self.get_aggregated_metrics(24)  # Last 24 hours
            current_metrics = self.get_current_metrics()
            
            export_data = {
                "export_timestamp": current_time.isoformat(),
                "export_format": format_type,
                "collector_info": {
                    "version": "1.0.0",
                    "issue": "#1300",
                    "component": "AsyncAuthMetricsCollector"
                },
                "collector_status": status,
                "current_metrics": current_metrics,
                "recent_snapshots": recent_snapshots,
                "aggregated_metrics": aggregated_data
            }
            
            self._total_exports += 1
            logger.debug(f"Exported metrics in {format_type} format ({len(recent_snapshots)} snapshots, {len(aggregated_data)} aggregations)")
            
            return export_data
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return {
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "collector_status": self._status.value
            }
    
    async def _collection_loop(self) -> None:
        """Main collection loop that runs in the background."""
        logger.info("Starting metrics collection loop")
        
        while True:
            try:
                if self._status == CollectorStatus.RUNNING:
                    await self._collect_metrics()
                elif self._status == CollectorStatus.STOPPING:
                    break
                
                await asyncio.sleep(self.config.collection_interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("Collection loop cancelled")
                break
            except Exception as e:
                self._collection_errors += 1
                logger.error(f"Error in collection loop: {e}")
                await asyncio.sleep(self.config.collection_interval_seconds)
    
    async def _aggregation_loop(self) -> None:
        """Aggregation loop that creates summary statistics."""
        logger.info("Starting metrics aggregation loop")
        
        while True:
            try:
                if self._status == CollectorStatus.RUNNING:
                    await self._aggregate_metrics()
                elif self._status == CollectorStatus.STOPPING:
                    break
                
                await asyncio.sleep(self.config.aggregation_interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("Aggregation loop cancelled")
                break
            except Exception as e:
                self._aggregation_errors += 1
                logger.error(f"Error in aggregation loop: {e}")
                await asyncio.sleep(self.config.aggregation_interval_seconds)
    
    async def _health_check_loop(self) -> None:
        """Health check loop for self-monitoring."""
        logger.info("Starting health check loop")
        
        while True:
            try:
                if self._status in [CollectorStatus.RUNNING, CollectorStatus.PAUSED]:
                    await self._perform_health_check()
                elif self._status == CollectorStatus.STOPPING:
                    break
                
                await asyncio.sleep(self.config.health_check_interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(self.config.health_check_interval_seconds)
    
    async def _alert_check_loop(self) -> None:
        """Alert checking loop for anomaly detection."""
        logger.info("Starting alert check loop")
        
        while True:
            try:
                if self._status == CollectorStatus.RUNNING:
                    await self._check_alerts()
                elif self._status == CollectorStatus.STOPPING:
                    break
                
                await asyncio.sleep(self.config.alert_check_interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("Alert check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in alert check loop: {e}")
                await asyncio.sleep(self.config.alert_check_interval_seconds)
    
    async def _collect_metrics(self) -> None:
        """Collect current metrics and create a snapshot."""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Get metrics from auth monitor
            global_metrics = get_auth_monitoring_metrics()
            
            # Extract relevant data
            if "global_metrics" in global_metrics:
                gm = global_metrics["global_metrics"]
                
                snapshot = MetricSnapshot(
                    timestamp=current_time,
                    auth_attempts=gm.get("auth_attempts", 0),
                    auth_successes=gm.get("auth_successes", 0),
                    auth_failures=gm.get("auth_failures", 0),
                    auth_success_rate=gm.get("auth_success_rate", 100.0),
                    token_validations=gm.get("token_validations", 0),
                    token_validation_successes=gm.get("token_validation_successes", 0),
                    token_validation_failures=gm.get("token_validation_failures", 0),
                    session_creations=gm.get("session_creations", 0),
                    session_invalidations=gm.get("session_invalidations", 0),
                    connection_upgrades=gm.get("connection_upgrades", 0),
                    connection_upgrade_successes=gm.get("connection_upgrade_successes", 0)
                )
                
                # Add latency data if available
                if "latency_percentiles" in gm:
                    lp = gm["latency_percentiles"]
                    snapshot.avg_latency_ms = lp.get("p50", 0.0)
                    snapshot.p95_latency_ms = lp.get("p95", 0.0)
                
                # Add session/connection counts
                snapshot.active_sessions = global_metrics.get("active_sessions_count", 0)
                snapshot.active_connections = global_metrics.get("active_connections_count", 0)
                
                # Store snapshot
                with self._lock:
                    self._metric_snapshots.append(snapshot)
                
                self._total_collections += 1
                self._last_collection_time = current_time
                
                logger.debug(f"Collected metrics snapshot: {snapshot.auth_attempts} attempts, {snapshot.auth_success_rate:.1f}% success rate")
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            raise
    
    async def _aggregate_metrics(self) -> None:
        """Aggregate recent snapshots into summary statistics."""
        try:
            current_time = datetime.now(timezone.utc)
            start_time = current_time - timedelta(seconds=self.config.aggregation_interval_seconds)
            
            # Get snapshots from the aggregation period
            relevant_snapshots = []
            with self._lock:
                for snapshot in self._metric_snapshots:
                    if snapshot.timestamp >= start_time:
                        relevant_snapshots.append(snapshot)
            
            if not relevant_snapshots:
                logger.debug("No snapshots available for aggregation")
                return
            
            # Calculate aggregated metrics
            total_attempts = sum(s.auth_attempts for s in relevant_snapshots)
            total_successes = sum(s.auth_successes for s in relevant_snapshots)
            total_failures = sum(s.auth_failures for s in relevant_snapshots)
            
            # Calculate averages and peaks
            success_rates = [s.auth_success_rate for s in relevant_snapshots if s.auth_attempts > 0]
            avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 100.0
            
            latencies = [s.avg_latency_ms for s in relevant_snapshots if s.avg_latency_ms > 0]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
            min_latency = min(latencies) if latencies else 0.0
            max_latency = max(latencies) if latencies else 0.0
            
            p95_latencies = [s.p95_latency_ms for s in relevant_snapshots if s.p95_latency_ms > 0]
            avg_p95_latency = sum(p95_latencies) / len(p95_latencies) if p95_latencies else 0.0
            
            peak_sessions = max((s.active_sessions for s in relevant_snapshots), default=0)
            peak_connections = max((s.active_connections for s in relevant_snapshots), default=0)
            
            # Create aggregated metrics
            aggregated = AggregatedMetrics(
                start_time=start_time,
                end_time=current_time,
                total_auth_attempts=total_attempts,
                total_auth_successes=total_successes,
                total_auth_failures=total_failures,
                avg_success_rate=avg_success_rate,
                min_latency_ms=min_latency,
                max_latency_ms=max_latency,
                avg_latency_ms=avg_latency,
                p95_latency_ms=avg_p95_latency,
                total_session_creations=sum(s.session_creations for s in relevant_snapshots),
                total_connection_upgrades=sum(s.connection_upgrades for s in relevant_snapshots),
                peak_active_sessions=peak_sessions,
                peak_active_connections=peak_connections
            )
            
            # Store aggregated metrics
            with self._lock:
                self._aggregated_metrics.append(aggregated)
            
            self._total_aggregations += 1
            self._last_aggregation_time = current_time
            
            logger.debug(f"Aggregated metrics: {len(relevant_snapshots)} snapshots, {total_attempts} attempts, {avg_success_rate:.1f}% avg success rate")
            
        except Exception as e:
            logger.error(f"Error aggregating metrics: {e}")
            raise
    
    async def _perform_health_check(self) -> None:
        """Perform health check on the collector itself."""
        try:
            current_time = datetime.now(timezone.utc)
            issues = []
            
            # Check if collection is working
            if self._last_collection_time:
                time_since_collection = (current_time - self._last_collection_time).total_seconds()
                if time_since_collection > self.config.collection_interval_seconds * 3:
                    issues.append(f"Collection stalled: {time_since_collection:.1f}s since last collection")
            
            # Check error rates
            if self._total_collections > 0:
                collection_error_rate = (self._collection_errors / self._total_collections) * 100
                if collection_error_rate > 10.0:  # >10% error rate
                    issues.append(f"High collection error rate: {collection_error_rate:.1f}%")
            
            if self._total_aggregations > 0:
                aggregation_error_rate = (self._aggregation_errors / self._total_aggregations) * 100
                if aggregation_error_rate > 10.0:  # >10% error rate
                    issues.append(f"High aggregation error rate: {aggregation_error_rate:.1f}%")
            
            # Log health status
            if issues:
                logger.warning(f"Collector health issues detected: {'; '.join(issues)}")
            else:
                logger.debug("Collector health check passed")
                
        except Exception as e:
            logger.error(f"Error in health check: {e}")
    
    async def _check_alerts(self) -> None:
        """Check for alert conditions in recent metrics."""
        try:
            # Get recent snapshots for alert analysis
            recent_snapshots = []
            with self._lock:
                if len(self._metric_snapshots) >= 3:  # Need at least 3 snapshots for trend analysis
                    recent_snapshots = list(self._metric_snapshots)[-3:]
            
            if not recent_snapshots:
                return
            
            current_time = datetime.now(timezone.utc)
            latest_snapshot = recent_snapshots[-1]
            
            # Check authentication failure rate alert
            if latest_snapshot.auth_attempts > 5:  # Only alert if we have enough samples
                failure_rate = 100.0 - latest_snapshot.auth_success_rate
                if failure_rate > self.config.alert_failure_rate_threshold:
                    await self._generate_alert(
                        "high_auth_failure_rate",
                        f"Authentication failure rate is {failure_rate:.1f}% (threshold: {self.config.alert_failure_rate_threshold}%)",
                        {"failure_rate": failure_rate, "attempts": latest_snapshot.auth_attempts}
                    )
            
            # Check latency alert
            if latest_snapshot.p95_latency_ms > self.config.alert_latency_threshold_ms:
                await self._generate_alert(
                    "high_latency",
                    f"P95 authentication latency is {latest_snapshot.p95_latency_ms:.1f}ms (threshold: {self.config.alert_latency_threshold_ms}ms)",
                    {"p95_latency_ms": latest_snapshot.p95_latency_ms}
                )
            
            # Check connection upgrade failure rate
            if latest_snapshot.connection_upgrades > 3:
                connection_failure_rate = 100.0 - latest_snapshot.connection_upgrade_successes / latest_snapshot.connection_upgrades * 100
                if connection_failure_rate > self.config.alert_connection_failure_threshold:
                    await self._generate_alert(
                        "high_connection_failure_rate",
                        f"Connection upgrade failure rate is {connection_failure_rate:.1f}% (threshold: {self.config.alert_connection_failure_threshold}%)",
                        {"connection_failure_rate": connection_failure_rate, "upgrades": latest_snapshot.connection_upgrades}
                    )
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    async def _generate_alert(self, alert_type: str, message: str, metadata: Dict[str, Any]) -> None:
        """Generate an alert with suppression logic."""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Check alert suppression (don't spam the same alert)
            suppression_duration = timedelta(minutes=5)  # Suppress same alert for 5 minutes
            if alert_type in self._alert_suppression:
                if current_time - self._alert_suppression[alert_type] < suppression_duration:
                    return  # Alert suppressed
            
            # Generate alert
            alert_data = {
                "alert_type": alert_type,
                "message": message,
                "timestamp": current_time.isoformat(),
                "severity": "warning",  # Could be made configurable
                "component": "AsyncAuthMetricsCollector",
                "issue": "#1300",
                "metadata": metadata
            }
            
            # Log alert
            logger.warning(f"ALERT [{alert_type.upper()}]: {message}", extra={"alert_data": alert_data})
            
            # Update alert tracking
            self._alerts_generated += 1
            self._last_alert_time = current_time
            self._alert_suppression[alert_type] = current_time
            
        except Exception as e:
            logger.error(f"Error generating alert: {e}")
    
    def _calculate_max_snapshots(self) -> int:
        """Calculate maximum number of snapshots to retain."""
        snapshots_per_hour = 3600 / self.config.collection_interval_seconds
        return int(snapshots_per_hour * self.config.retention_hours)
    
    def _calculate_max_aggregations(self) -> int:
        """Calculate maximum number of aggregations to retain."""
        aggregations_per_hour = 3600 / self.config.aggregation_interval_seconds
        return int(aggregations_per_hour * self.config.retention_hours)


# Global instance for async metrics collection
_async_metrics_collector: Optional[AsyncAuthMetricsCollector] = None
_collector_lock = threading.Lock()


def get_async_auth_metrics_collector(config: Optional[CollectionConfig] = None) -> AsyncAuthMetricsCollector:
    """Get or create the global async authentication metrics collector."""
    global _async_metrics_collector
    
    if _async_metrics_collector is None:
        with _collector_lock:
            if _async_metrics_collector is None:
                _async_metrics_collector = AsyncAuthMetricsCollector(config)
                logger.info("Created global AsyncAuthMetricsCollector for Issue #1300")
    
    return _async_metrics_collector


async def start_metrics_collection(config: Optional[CollectionConfig] = None) -> AsyncAuthMetricsCollector:
    """Start the async metrics collection service."""
    collector = get_async_auth_metrics_collector(config)
    await collector.start()
    return collector


async def stop_metrics_collection() -> None:
    """Stop the async metrics collection service."""
    global _async_metrics_collector
    if _async_metrics_collector:
        await _async_metrics_collector.stop()


def get_collector_status() -> Dict[str, Any]:
    """Get the status of the metrics collector."""
    if _async_metrics_collector:
        return _async_metrics_collector.get_status()
    else:
        return {"status": "not_initialized"}


async def export_collected_metrics(format_type: str = "json") -> Dict[str, Any]:
    """Export collected metrics."""
    if _async_metrics_collector:
        return await _async_metrics_collector.export_metrics(format_type)
    else:
        return {"error": "Collector not initialized"}


# Export public interface
__all__ = [
    "AsyncAuthMetricsCollector",
    "CollectionConfig",
    "MetricSnapshot",
    "AggregatedMetrics",
    "CollectorStatus",
    "get_async_auth_metrics_collector",
    "start_metrics_collection",
    "stop_metrics_collection",
    "get_collector_status",
    "export_collected_metrics"
]