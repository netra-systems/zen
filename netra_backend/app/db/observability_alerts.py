"""Database Observability Alerts

Alert checking and handling for database monitoring.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from netra_backend.app.db.observability_metrics import AlertThresholds, DatabaseMetrics
from netra_backend.app.db.postgres import async_engine
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ConnectionAlertChecker:
    """Check connection-related alerts."""
    
    @staticmethod
    def check_pool_availability() -> bool:
        """Check if pool is available for checking."""
        return (async_engine and hasattr(async_engine, 'pool') and 
                hasattr(async_engine.pool, 'size') and 
                hasattr(async_engine.pool, '_max_overflow'))

    @staticmethod
    def calculate_usage_rate(metrics: DatabaseMetrics) -> float:
        """Calculate connection usage rate."""
        if not ConnectionAlertChecker.check_pool_availability():
            return 0.0
        
        pool = async_engine.pool
        max_connections = pool.size() + pool._max_overflow
        return metrics.total_connections / max_connections if max_connections > 0 else 0.0

    @staticmethod
    def create_connection_usage_alert(usage_rate: float, threshold: float) -> Dict[str, Any]:
        """Create connection usage alert."""
        return {
            'type': 'connection_usage_high', 'severity': 'warning',
            'message': f'Connection usage at {usage_rate:.1%}',
            'value': usage_rate, 'threshold': threshold
        }

    @staticmethod
    def check_connection_alerts(alerts: List[Dict], metrics: DatabaseMetrics, thresholds: AlertThresholds) -> None:
        """Check for connection-related alerts."""
        usage_rate = ConnectionAlertChecker.calculate_usage_rate(metrics)
        
        if usage_rate > thresholds.max_connection_usage:
            alert = ConnectionAlertChecker.create_connection_usage_alert(usage_rate, thresholds.max_connection_usage)
            alerts.append(alert)


class QueryAlertChecker:
    """Check query performance alerts."""
    
    @staticmethod
    def create_slow_query_alert(avg_time: float, threshold: float) -> Dict[str, Any]:
        """Create slow query alert."""
        return {
            'type': 'slow_queries', 'severity': 'warning',
            'message': f'Average query time {avg_time:.2f}s',
            'value': avg_time, 'threshold': threshold
        }

    @staticmethod
    def create_slow_query_rate_alert(rate: float, threshold: float) -> Dict[str, Any]:
        """Create slow query rate alert."""
        return {
            'type': 'slow_query_rate_high', 'severity': 'warning',
            'message': f'Slow query rate at {rate:.1%}',
            'value': rate, 'threshold': threshold
        }

    @staticmethod
    def check_avg_query_time(alerts: List[Dict], metrics: DatabaseMetrics, thresholds: AlertThresholds) -> None:
        """Check average query time alert."""
        if metrics.avg_query_time > thresholds.max_avg_query_time:
            alert = QueryAlertChecker.create_slow_query_alert(metrics.avg_query_time, thresholds.max_avg_query_time)
            alerts.append(alert)

    @staticmethod
    def check_slow_query_rate(alerts: List[Dict], metrics: DatabaseMetrics, thresholds: AlertThresholds) -> None:
        """Check slow query rate alert."""
        if metrics.total_queries > 0:
            slow_query_rate = metrics.slow_queries / metrics.total_queries
            if slow_query_rate > thresholds.max_slow_query_rate:
                alert = QueryAlertChecker.create_slow_query_rate_alert(slow_query_rate, thresholds.max_slow_query_rate)
                alerts.append(alert)

    @staticmethod
    def check_query_performance_alerts(alerts: List[Dict], metrics: DatabaseMetrics, thresholds: AlertThresholds) -> None:
        """Check for query performance alerts."""
        QueryAlertChecker.check_avg_query_time(alerts, metrics, thresholds)
        QueryAlertChecker.check_slow_query_rate(alerts, metrics, thresholds)


class CacheAlertChecker:
    """Check cache-related alerts."""
    
    @staticmethod
    def create_cache_hit_rate_alert(hit_rate: float, threshold: float) -> Dict[str, Any]:
        """Create cache hit rate alert."""
        return {
            'type': 'cache_hit_rate_low', 'severity': 'info',
            'message': f'Cache hit rate at {hit_rate:.1%}',
            'value': hit_rate, 'threshold': threshold
        }

    @staticmethod
    def check_cache_alerts(alerts: List[Dict], metrics: DatabaseMetrics, thresholds: AlertThresholds) -> None:
        """Check for cache-related alerts."""
        if metrics.cache_hit_rate < thresholds.min_cache_hit_rate:
            alert = CacheAlertChecker.create_cache_hit_rate_alert(metrics.cache_hit_rate, thresholds.min_cache_hit_rate)
            alerts.append(alert)


class TransactionAlertChecker:
    """Check transaction-related alerts."""
    
    @staticmethod
    def create_active_transactions_alert(count: int, threshold: int) -> Dict[str, Any]:
        """Create active transactions alert."""
        return {
            'type': 'active_transactions_high', 'severity': 'critical',
            'message': f'{count} active transactions',
            'value': count, 'threshold': threshold
        }

    @staticmethod
    def check_transaction_alerts(alerts: List[Dict], metrics: DatabaseMetrics, thresholds: AlertThresholds) -> None:
        """Check for transaction-related alerts."""
        if metrics.active_transactions > thresholds.max_active_transactions:
            alert = TransactionAlertChecker.create_active_transactions_alert(
                metrics.active_transactions, 
                thresholds.max_active_transactions
            )
            alerts.append(alert)


class AlertHandler:
    """Handle database alerts."""
    
    @staticmethod
    def add_timestamp_to_alert(alert: Dict[str, Any]) -> None:
        """Add timestamp to alert."""
        alert['timestamp'] = datetime.now().isoformat()

    @staticmethod
    def _log_with_severity_level(severity: str, message: str) -> None:
        """Log message with appropriate severity level."""
        if severity == 'critical':
            logger.critical(f"Database Alert: {message}")
        elif severity == 'warning':
            logger.warning(f"Database Alert: {message}")
        else:
            logger.info(f"Database Alert: {message}")

    @staticmethod
    def log_alert_by_severity(alert: Dict[str, Any]) -> None:
        """Log alert based on severity."""
        severity = alert['severity']
        message = alert['message']
        AlertHandler._log_with_severity_level(severity, message)

    @staticmethod
    async def call_alert_callback(alert: Dict[str, Any], callback) -> None:
        """Call alert callback if configured."""
        if callback:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Error calling alert callback: {e}")

    @staticmethod
    async def handle_alert(alert: Dict[str, Any], storage, callback=None) -> None:
        """Handle database alert."""
        AlertHandler.add_timestamp_to_alert(alert)
        storage.store_alert(alert)
        AlertHandler.log_alert_by_severity(alert)
        await AlertHandler.call_alert_callback(alert, callback)


class AlertOrchestrator:
    """Orchestrate all alert checking."""
    
    @staticmethod
    def collect_all_alerts(metrics: DatabaseMetrics, thresholds: AlertThresholds) -> List[Dict]:
        """Collect all alert types."""
        alerts = []
        ConnectionAlertChecker.check_connection_alerts(alerts, metrics, thresholds)
        QueryAlertChecker.check_query_performance_alerts(alerts, metrics, thresholds)
        CacheAlertChecker.check_cache_alerts(alerts, metrics, thresholds)
        TransactionAlertChecker.check_transaction_alerts(alerts, metrics, thresholds)
        return alerts

    @staticmethod
    async def process_all_alerts(alerts: List[Dict], storage, callback=None) -> None:
        """Process all collected alerts."""
        for alert in alerts:
            await AlertHandler.handle_alert(alert, storage, callback)

    @staticmethod
    async def _execute_alert_workflow(metrics: DatabaseMetrics, thresholds: AlertThresholds, storage, callback):
        """Execute the alert checking and processing workflow."""
        alerts = AlertOrchestrator.collect_all_alerts(metrics, thresholds)
        await AlertOrchestrator.process_all_alerts(alerts, storage, callback)
    
    @staticmethod
    async def check_and_process_alerts(metrics: DatabaseMetrics, thresholds: AlertThresholds, storage, callback=None) -> None:
        """Check for alerts and process them."""
        try:
            await AlertOrchestrator._execute_alert_workflow(metrics, thresholds, storage, callback)
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")


# Convenience functions for backward compatibility
def check_connection_alerts(alerts: List[Dict], metrics: DatabaseMetrics, thresholds: AlertThresholds) -> None:
    """Check connection alerts (backward compatibility)."""
    ConnectionAlertChecker.check_connection_alerts(alerts, metrics, thresholds)

def check_query_performance_alerts(alerts: List[Dict], metrics: DatabaseMetrics, thresholds: AlertThresholds) -> None:
    """Check query performance alerts (backward compatibility)."""
    QueryAlertChecker.check_query_performance_alerts(alerts, metrics, thresholds)

def check_cache_alerts(alerts: List[Dict], metrics: DatabaseMetrics, thresholds: AlertThresholds) -> None:
    """Check cache alerts (backward compatibility)."""
    CacheAlertChecker.check_cache_alerts(alerts, metrics, thresholds)

def check_transaction_alerts(alerts: List[Dict], metrics: DatabaseMetrics, thresholds: AlertThresholds) -> None:
    """Check transaction alerts (backward compatibility)."""
    TransactionAlertChecker.check_transaction_alerts(alerts, metrics, thresholds)

async def handle_alert(alert: Dict[str, Any], storage, callback=None) -> None:
    """Handle alert (backward compatibility)."""
    await AlertHandler.handle_alert(alert, storage, callback)


class AlertManager:
    """High-level alert management interface."""
    
    def __init__(self, storage=None, callback=None):
        self.thresholds = AlertThresholds()
        self.storage = storage
        self.callback = callback
        self.orchestrator = AlertOrchestrator()
    
    def set_thresholds(self, **thresholds) -> None:
        """Update alert thresholds."""
        for key, value in thresholds.items():
            if hasattr(self.thresholds, key):
                setattr(self.thresholds, key, value)
    
    async def check_alerts(self, metrics: DatabaseMetrics) -> List[Dict[str, Any]]:
        """Check all alerts for given metrics."""
        return self.orchestrator.collect_all_alerts(metrics, self.thresholds)
    
    async def process_alerts(self, metrics: DatabaseMetrics) -> None:
        """Check and process all alerts."""
        if self.storage:
            await self.orchestrator.check_and_process_alerts(
                metrics, self.thresholds, self.storage, self.callback
            )