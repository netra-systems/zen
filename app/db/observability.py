"""Database Observability Dashboard

Provides comprehensive monitoring and metrics for database operations,
connection pools, and performance optimization.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque

from app.logging_config import central_logger
from app.db.postgres import async_engine, get_pool_status
from app.services.database.connection_monitor import get_connection_status
from app.db.query_cache import query_cache
from app.db.transaction_manager import transaction_manager

logger = central_logger.get_logger(__name__)


@dataclass
class DatabaseMetrics:
    """Comprehensive database metrics."""
    timestamp: datetime
    
    # Connection metrics
    active_connections: int = 0
    idle_connections: int = 0
    total_connections: int = 0
    connection_errors: int = 0
    connection_timeouts: int = 0
    
    # Query metrics
    total_queries: int = 0
    slow_queries: int = 0
    failed_queries: int = 0
    avg_query_time: float = 0.0
    max_query_time: float = 0.0
    
    # Transaction metrics
    active_transactions: int = 0
    committed_transactions: int = 0
    rolled_back_transactions: int = 0
    deadlocks: int = 0
    
    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_size: int = 0
    cache_hit_rate: float = 0.0
    
    # Performance metrics
    queries_per_second: float = 0.0
    connections_per_second: float = 0.0
    avg_response_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


@dataclass
class AlertThresholds:
    """Alert thresholds for database monitoring."""
    max_connection_usage: float = 0.8  # 80% of pool
    max_avg_query_time: float = 1.0  # 1 second
    max_slow_query_rate: float = 0.1  # 10% of queries
    min_cache_hit_rate: float = 0.5  # 50%
    max_active_transactions: int = 50
    max_deadlock_rate: float = 0.01  # 1% of transactions


class DatabaseObservability:
    """Database observability and monitoring system."""
    
    def __init__(self, alert_thresholds: Optional[AlertThresholds] = None):
        """Initialize observability system."""
        self.alert_thresholds = alert_thresholds or AlertThresholds()
        self.metrics_history: deque = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        self.alerts: deque = deque(maxlen=100)  # Keep last 100 alerts
        
        # Performance tracking
        self.query_times: deque = deque(maxlen=1000)  # Last 1000 queries
        self.connection_events: deque = deque(maxlen=1000)  # Last 1000 connection events
        
        # Background monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        self._collection_interval = 60  # 1 minute
        
        # Current metrics
        self.current_metrics = DatabaseMetrics(timestamp=datetime.now())
        
        # Alert callback
        self.alert_callback: Optional[callable] = None
    
    async def start_monitoring(self) -> None:
        """Start background monitoring."""
        if self._running:
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Database observability monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Database observability monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._collect_metrics()
                await self._check_alerts()
                await asyncio.sleep(self._collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Database monitoring error: {e}")
                await asyncio.sleep(self._collection_interval)
    
    async def _collect_metrics(self) -> None:
        """Collect comprehensive database metrics."""
        timestamp = datetime.now()
        metrics = DatabaseMetrics(timestamp=timestamp)
        
        try:
            # Collect connection metrics
            await self._collect_connection_metrics(metrics)
            
            # Collect query metrics
            await self._collect_query_metrics(metrics)
            
            # Collect transaction metrics
            await self._collect_transaction_metrics(metrics)
            
            # Collect cache metrics
            await self._collect_cache_metrics(metrics)
            
            # Calculate performance metrics
            await self._calculate_performance_metrics(metrics)
            
            # Store metrics
            self.current_metrics = metrics
            self.metrics_history.append(metrics)
            
            logger.debug(f"Collected database metrics: {metrics.total_queries} queries, "
                        f"{metrics.active_connections} connections")
            
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")
    
    async def _collect_connection_metrics(self, metrics: DatabaseMetrics) -> None:
        """Collect connection pool metrics."""
        try:
            connection_status = await get_connection_status()
            pool_metrics = connection_status.get('pool_metrics', {})
            
            # Async pool metrics
            async_pool = pool_metrics.get('async_pool')
            if async_pool and not async_pool.get('error'):
                metrics.total_connections = async_pool.get('total_connections', 0)
                metrics.active_connections = async_pool.get('checked_out', 0)
                metrics.idle_connections = async_pool.get('checked_in', 0)
            
            # Sync pool metrics
            sync_pool = pool_metrics.get('sync_pool')
            if sync_pool and not sync_pool.get('error'):
                metrics.total_connections += sync_pool.get('total_connections', 0)
                metrics.active_connections += sync_pool.get('checked_out', 0)
                metrics.idle_connections += sync_pool.get('checked_in', 0)
            
        except Exception as e:
            logger.error(f"Error collecting connection metrics: {e}")
    
    async def _collect_query_metrics(self, metrics: DatabaseMetrics) -> None:
        """Collect query performance metrics."""
        try:
            cache_metrics = query_cache.get_metrics()
            
            metrics.total_queries = cache_metrics.get('total_queries', 0)
            metrics.avg_query_time = cache_metrics.get('avg_query_time', 0.0)
            
            # Calculate slow queries
            slow_query_threshold = 1.0  # 1 second
            slow_queries = sum(1 for qt in self.query_times if qt > slow_query_threshold)
            metrics.slow_queries = slow_queries
            
            if self.query_times:
                metrics.max_query_time = max(self.query_times)
            
        except Exception as e:
            logger.error(f"Error collecting query metrics: {e}")
    
    async def _collect_transaction_metrics(self, metrics: DatabaseMetrics) -> None:
        """Collect transaction metrics."""
        try:
            tx_stats = transaction_manager.get_transaction_stats()
            
            metrics.active_transactions = tx_stats.get('active_transactions', 0)
            
            # Additional transaction metrics would come from database logs
            # or custom transaction tracking
            
        except Exception as e:
            logger.error(f"Error collecting transaction metrics: {e}")
    
    async def _collect_cache_metrics(self, metrics: DatabaseMetrics) -> None:
        """Collect cache performance metrics."""
        try:
            cache_metrics_data = query_cache.get_metrics()
            
            metrics.cache_hits = cache_metrics_data.get('hits', 0)
            metrics.cache_misses = cache_metrics_data.get('misses', 0)
            metrics.cache_size = cache_metrics_data.get('cache_size', 0)
            metrics.cache_hit_rate = cache_metrics_data.get('hit_rate', 0.0)
            
        except Exception as e:
            logger.error(f"Error collecting cache metrics: {e}")
    
    async def _calculate_performance_metrics(self, metrics: DatabaseMetrics) -> None:
        """Calculate derived performance metrics."""
        try:
            # Calculate queries per second
            if len(self.metrics_history) > 1:
                prev_metrics = self.metrics_history[-1]
                time_diff = (metrics.timestamp - prev_metrics.timestamp).total_seconds()
                
                if time_diff > 0:
                    query_diff = metrics.total_queries - prev_metrics.total_queries
                    metrics.queries_per_second = query_diff / time_diff
                    
                    conn_diff = metrics.total_connections - prev_metrics.total_connections
                    metrics.connections_per_second = abs(conn_diff) / time_diff
            
            # Calculate average response time
            if self.query_times:
                metrics.avg_response_time = sum(self.query_times) / len(self.query_times)
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
    
    async def _check_alerts(self) -> None:
        """Check for alert conditions."""
        try:
            alerts = []
            metrics = self.current_metrics
            
            # Connection usage alert
            if async_engine and hasattr(async_engine, 'pool'):
                pool = async_engine.pool
                if hasattr(pool, 'size') and hasattr(pool, '_max_overflow'):
                    max_connections = pool.size() + pool._max_overflow
                    usage_rate = metrics.total_connections / max_connections
                    
                    if usage_rate > self.alert_thresholds.max_connection_usage:
                        alerts.append({
                            'type': 'connection_usage_high',
                            'severity': 'warning',
                            'message': f'Connection usage at {usage_rate:.1%}',
                            'value': usage_rate,
                            'threshold': self.alert_thresholds.max_connection_usage
                        })
            
            # Query performance alerts
            if metrics.avg_query_time > self.alert_thresholds.max_avg_query_time:
                alerts.append({
                    'type': 'slow_queries',
                    'severity': 'warning',
                    'message': f'Average query time {metrics.avg_query_time:.2f}s',
                    'value': metrics.avg_query_time,
                    'threshold': self.alert_thresholds.max_avg_query_time
                })
            
            # Slow query rate alert
            if metrics.total_queries > 0:
                slow_query_rate = metrics.slow_queries / metrics.total_queries
                if slow_query_rate > self.alert_thresholds.max_slow_query_rate:
                    alerts.append({
                        'type': 'slow_query_rate_high',
                        'severity': 'warning',
                        'message': f'Slow query rate at {slow_query_rate:.1%}',
                        'value': slow_query_rate,
                        'threshold': self.alert_thresholds.max_slow_query_rate
                    })
            
            # Cache hit rate alert
            if metrics.cache_hit_rate < self.alert_thresholds.min_cache_hit_rate:
                alerts.append({
                    'type': 'cache_hit_rate_low',
                    'severity': 'info',
                    'message': f'Cache hit rate at {metrics.cache_hit_rate:.1%}',
                    'value': metrics.cache_hit_rate,
                    'threshold': self.alert_thresholds.min_cache_hit_rate
                })
            
            # Active transactions alert
            if metrics.active_transactions > self.alert_thresholds.max_active_transactions:
                alerts.append({
                    'type': 'active_transactions_high',
                    'severity': 'critical',
                    'message': f'{metrics.active_transactions} active transactions',
                    'value': metrics.active_transactions,
                    'threshold': self.alert_thresholds.max_active_transactions
                })
            
            # Process alerts
            for alert in alerts:
                await self._handle_alert(alert)
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    async def _handle_alert(self, alert: Dict[str, Any]) -> None:
        """Handle database alert."""
        alert['timestamp'] = datetime.now().isoformat()
        self.alerts.append(alert)
        
        # Log alert
        severity = alert['severity']
        message = alert['message']
        
        if severity == 'critical':
            logger.critical(f"Database Alert: {message}")
        elif severity == 'warning':
            logger.warning(f"Database Alert: {message}")
        else:
            logger.info(f"Database Alert: {message}")
        
        # Call alert callback if configured
        if self.alert_callback:
            try:
                await self.alert_callback(alert)
            except Exception as e:
                logger.error(f"Error calling alert callback: {e}")
    
    def record_query_time(self, duration: float) -> None:
        """Record query execution time."""
        self.query_times.append(duration)
    
    def record_connection_event(self, event_type: str, details: Dict[str, Any] = None) -> None:
        """Record connection event."""
        event = {
            'timestamp': time.time(),
            'type': event_type,
            'details': details or {}
        }
        self.connection_events.append(event)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current database metrics."""
        return self.current_metrics.to_dict()
    
    def get_metrics_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get metrics history for specified hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        return [
            metrics.to_dict()
            for metrics in self.metrics_history
            if metrics.timestamp >= cutoff
        ]
    
    def get_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alerts from specified time period."""
        cutoff = datetime.now() - timedelta(hours=hours)
        cutoff_iso = cutoff.isoformat()
        
        return [
            alert for alert in self.alerts
            if alert.get('timestamp', '') >= cutoff_iso
        ]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.metrics_history:
            return {}
        
        recent_metrics = list(self.metrics_history)[-60:]  # Last hour
        
        # Calculate averages
        avg_query_time = sum(m.avg_query_time for m in recent_metrics) / len(recent_metrics)
        avg_connections = sum(m.active_connections for m in recent_metrics) / len(recent_metrics)
        avg_cache_hit_rate = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)
        
        # Calculate trends
        if len(recent_metrics) >= 2:
            first_half = recent_metrics[:len(recent_metrics)//2]
            second_half = recent_metrics[len(recent_metrics)//2:]
            
            query_time_trend = (
                sum(m.avg_query_time for m in second_half) / len(second_half) -
                sum(m.avg_query_time for m in first_half) / len(first_half)
            )
            
            connection_trend = (
                sum(m.active_connections for m in second_half) / len(second_half) -
                sum(m.active_connections for m in first_half) / len(first_half)
            )
        else:
            query_time_trend = 0.0
            connection_trend = 0.0
        
        return {
            'avg_query_time': avg_query_time,
            'avg_connections': avg_connections,
            'avg_cache_hit_rate': avg_cache_hit_rate,
            'query_time_trend': query_time_trend,
            'connection_trend': connection_trend,
            'total_queries': sum(m.total_queries for m in recent_metrics),
            'slow_queries': sum(m.slow_queries for m in recent_metrics),
            'cache_hits': sum(m.cache_hits for m in recent_metrics),
            'cache_misses': sum(m.cache_misses for m in recent_metrics)
        }
    
    def set_alert_callback(self, callback: callable) -> None:
        """Set callback function for alerts."""
        self.alert_callback = callback


# Global observability instance
database_observability = DatabaseObservability()


async def setup_database_observability(
    alert_callback: Optional[callable] = None
) -> None:
    """Setup database observability monitoring."""
    if alert_callback:
        database_observability.set_alert_callback(alert_callback)
    
    await database_observability.start_monitoring()
    logger.info("Database observability setup complete")


async def get_database_dashboard() -> Dict[str, Any]:
    """Get comprehensive database dashboard data."""
    return {
        'current_metrics': database_observability.get_current_metrics(),
        'metrics_history': database_observability.get_metrics_history(hours=1),
        'recent_alerts': database_observability.get_alerts(hours=1),
        'performance_summary': database_observability.get_performance_summary(),
        'cache_metrics': query_cache.get_metrics(),
        'transaction_stats': transaction_manager.get_transaction_stats()
    }