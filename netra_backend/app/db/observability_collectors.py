"""Database Observability Collectors

Metric collection functions for database monitoring.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from app.logging_config import central_logger
from app.db.postgres import async_engine, get_pool_status
from app.services.database.connection_monitor import get_connection_status
from app.db.query_cache import query_cache
from app.db.transaction_manager import transaction_manager
from netra_backend.app.observability_metrics import DatabaseMetrics, PerformanceCalculator

logger = central_logger.get_logger(__name__)


class ConnectionMetricsCollector:
    """Collect connection pool metrics."""
    
    @staticmethod
    async def collect_async_pool_metrics(metrics: DatabaseMetrics, async_pool: Dict[str, Any]) -> None:
        """Collect async pool metrics."""
        if async_pool and not async_pool.get('error'):
            metrics.total_connections = async_pool.get('total_connections', 0)
            metrics.active_connections = async_pool.get('checked_out', 0)
            metrics.idle_connections = async_pool.get('checked_in', 0)

    @staticmethod
    async def collect_sync_pool_metrics(metrics: DatabaseMetrics, sync_pool: Dict[str, Any]) -> None:
        """Collect sync pool metrics."""
        if sync_pool and not sync_pool.get('error'):
            metrics.total_connections += sync_pool.get('total_connections', 0)
            metrics.active_connections += sync_pool.get('checked_out', 0)
            metrics.idle_connections += sync_pool.get('checked_in', 0)

    @staticmethod
    async def collect_connection_status(metrics: DatabaseMetrics) -> None:
        """Collect connection status metrics."""
        try:
            connection_status = await get_connection_status()
            pool_metrics = connection_status.get('pool_metrics', {})
            
            async_pool = pool_metrics.get('async_pool')
            await ConnectionMetricsCollector.collect_async_pool_metrics(metrics, async_pool)
            
            sync_pool = pool_metrics.get('sync_pool')
            await ConnectionMetricsCollector.collect_sync_pool_metrics(metrics, sync_pool)
            
        except Exception as e:
            logger.error(f"Error collecting connection metrics: {e}")


class QueryMetricsCollector:
    """Collect query performance metrics."""
    
    @staticmethod
    def calculate_slow_queries(query_times, threshold: float = 1.0) -> int:
        """Calculate number of slow queries."""
        return sum(1 for qt in query_times if qt > threshold)

    @staticmethod
    def get_max_query_time(query_times) -> float:
        """Get maximum query time."""
        return max(query_times) if query_times else 0.0

    @staticmethod
    async def collect_cache_query_metrics(metrics: DatabaseMetrics) -> None:
        """Collect query metrics from cache."""
        cache_metrics = query_cache.get_metrics()
        metrics.total_queries = cache_metrics.get('total_queries', 0)
        metrics.avg_query_time = cache_metrics.get('avg_query_time', 0.0)

    @staticmethod
    async def collect_timing_metrics(metrics: DatabaseMetrics, query_times) -> None:
        """Collect query timing metrics."""
        slow_query_threshold = 1.0  # 1 second
        metrics.slow_queries = QueryMetricsCollector.calculate_slow_queries(query_times, slow_query_threshold)
        metrics.max_query_time = QueryMetricsCollector.get_max_query_time(query_times)

    @staticmethod
    async def collect_query_metrics(metrics: DatabaseMetrics, query_times) -> None:
        """Collect comprehensive query metrics."""
        try:
            await QueryMetricsCollector.collect_cache_query_metrics(metrics)
            await QueryMetricsCollector.collect_timing_metrics(metrics, query_times)
        except Exception as e:
            logger.error(f"Error collecting query metrics: {e}")


class TransactionMetricsCollector:
    """Collect transaction metrics."""
    
    @staticmethod
    async def collect_active_transactions(metrics: DatabaseMetrics) -> None:
        """Collect active transaction count."""
        tx_stats = transaction_manager.get_transaction_stats()
        metrics.active_transactions = tx_stats.get('active_transactions', 0)

    @staticmethod
    async def collect_transaction_metrics(metrics: DatabaseMetrics) -> None:
        """Collect transaction metrics."""
        try:
            await TransactionMetricsCollector.collect_active_transactions(metrics)
            # Additional transaction metrics from database logs or custom tracking
        except Exception as e:
            logger.error(f"Error collecting transaction metrics: {e}")


class CacheMetricsCollector:
    """Collect cache performance metrics."""
    
    @staticmethod
    async def collect_cache_data(metrics: DatabaseMetrics) -> None:
        """Collect cache performance data."""
        cache_metrics_data = query_cache.get_metrics()
        
        metrics.cache_hits = cache_metrics_data.get('hits', 0)
        metrics.cache_misses = cache_metrics_data.get('misses', 0)
        metrics.cache_size = cache_metrics_data.get('cache_size', 0)
        metrics.cache_hit_rate = cache_metrics_data.get('hit_rate', 0.0)

    @staticmethod
    async def collect_cache_metrics(metrics: DatabaseMetrics) -> None:
        """Collect cache performance metrics."""
        try:
            await CacheMetricsCollector.collect_cache_data(metrics)
        except Exception as e:
            logger.error(f"Error collecting cache metrics: {e}")


class PerformanceMetricsCollector:
    """Collect derived performance metrics."""
    
    @staticmethod
    async def _calculate_per_second_rates(metrics: DatabaseMetrics, prev_metrics) -> None:
        """Calculate per-second performance rates."""
        metrics.queries_per_second = PerformanceCalculator.calculate_queries_per_second(metrics, prev_metrics)
        metrics.connections_per_second = PerformanceCalculator.calculate_connections_per_second(metrics, prev_metrics)

    @staticmethod
    async def calculate_rates(metrics: DatabaseMetrics, metrics_history, query_times) -> None:
        """Calculate performance rates."""
        if len(metrics_history) > 1:
            prev_metrics = metrics_history[-1]
            await PerformanceMetricsCollector._calculate_per_second_rates(metrics, prev_metrics)
        metrics.avg_response_time = PerformanceCalculator.calculate_average_response_time(query_times)

    @staticmethod
    async def collect_performance_metrics(metrics: DatabaseMetrics, metrics_history, query_times) -> None:
        """Calculate derived performance metrics."""
        try:
            await PerformanceMetricsCollector.calculate_rates(metrics, metrics_history, query_times)
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")


class MetricsCollectionOrchestrator:
    """Orchestrate all metric collection."""
    
    @staticmethod
    async def gather_all_metrics(metrics: DatabaseMetrics, metrics_history, query_times) -> None:
        """Gather all types of database metrics."""
        await ConnectionMetricsCollector.collect_connection_metrics(metrics)
        await QueryMetricsCollector.collect_query_metrics(metrics, query_times)
        await TransactionMetricsCollector.collect_transaction_metrics(metrics)
        await CacheMetricsCollector.collect_cache_metrics(metrics)
        await PerformanceMetricsCollector.collect_performance_metrics(metrics, metrics_history, query_times)

    @staticmethod
    async def collect_comprehensive_metrics(metrics_history, query_times) -> DatabaseMetrics:
        """Collect comprehensive database metrics."""
        timestamp = datetime.now()
        metrics = DatabaseMetrics(timestamp=timestamp)
        
        try:
            await MetricsCollectionOrchestrator.gather_all_metrics(metrics, metrics_history, query_times)
            return metrics
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")
            return metrics  # Return partial metrics on error


class MonitoringCycleManager:
    """Manage monitoring cycle execution."""
    
    @staticmethod
    async def execute_cycle_steps(collect_func, check_alerts_func, interval: int) -> None:
        """Execute monitoring cycle steps."""
        await collect_func()
        await check_alerts_func()
        await asyncio.sleep(interval)

    @staticmethod
    async def handle_cycle_error(error: Exception, interval: int) -> None:
        """Handle monitoring cycle error."""
        logger.error(f"Database monitoring error: {error}")
        await asyncio.sleep(interval)

    @staticmethod
    async def run_monitoring_cycle(
        collect_func, 
        check_alerts_func, 
        interval: int = 60, 
        running_flag=lambda: True
    ) -> None:
        """Run continuous monitoring cycle."""
        while running_flag():
            try:
                await MonitoringCycleManager.execute_cycle_steps(collect_func, check_alerts_func, interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                await MonitoringCycleManager.handle_cycle_error(e, interval)


# Convenience functions for backward compatibility
async def collect_connection_metrics(metrics: DatabaseMetrics) -> None:
    """Collect connection metrics (backward compatibility)."""
    await ConnectionMetricsCollector.collect_connection_status(metrics)

async def collect_query_metrics(metrics: DatabaseMetrics, query_times) -> None:
    """Collect query metrics (backward compatibility)."""
    await QueryMetricsCollector.collect_query_metrics(metrics, query_times)

async def collect_transaction_metrics(metrics: DatabaseMetrics) -> None:
    """Collect transaction metrics (backward compatibility)."""
    await TransactionMetricsCollector.collect_transaction_metrics(metrics)

async def collect_cache_metrics(metrics: DatabaseMetrics) -> None:
    """Collect cache metrics (backward compatibility)."""
    await CacheMetricsCollector.collect_cache_metrics(metrics)

async def calculate_performance_metrics(metrics: DatabaseMetrics, metrics_history, query_times) -> None:
    """Calculate performance metrics (backward compatibility)."""
    await PerformanceMetricsCollector.collect_performance_metrics(metrics, metrics_history, query_times)