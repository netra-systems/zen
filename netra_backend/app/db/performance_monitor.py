"""
Database Performance Monitor - Performance Monitoring Module

This module provides database performance monitoring capabilities for integration
tests and production monitoring of database operations.

Business Value Justification (BVJ):
- Segment: Platform/Internal - All customer segments benefit from database performance
- Business Goal: Ensure database performance meets SLAs for all customer tiers
- Value Impact: Performance monitoring prevents database bottlenecks affecting customers
- Strategic Impact: Enables proactive performance management and capacity planning
"""

import logging
import time
import asyncio
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class MonitoringType(Enum):
    """Types of database monitoring."""
    CONNECTION_POOL = "connection_pool"
    QUERY_PERFORMANCE = "query_performance"
    TRANSACTION_PERFORMANCE = "transaction_performance"
    GENERAL = "general"


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    monitoring_id: str
    monitoring_type: MonitoringType
    start_time: float
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    test_prefix: Optional[str] = None


class DatabasePerformanceMonitor:
    """
    Database Performance Monitor for tracking database operation performance.
    
    Provides monitoring capabilities for:
    - Connection pool performance and utilization
    - Query execution times and throughput
    - Transaction performance under load
    - Resource usage tracking
    """
    
    def __init__(self):
        """Initialize database performance monitor."""
        self._active_monitors: Dict[str, PerformanceMetrics] = {}
        self._completed_monitors: Dict[str, PerformanceMetrics] = {}
        logger.info("Database Performance Monitor initialized")
    
    async def start_monitoring(self, 
                             monitoring_type: str, 
                             test_prefix: Optional[str] = None,
                             **kwargs) -> str:
        """
        Start performance monitoring session.
        
        Args:
            monitoring_type: Type of monitoring to perform
            test_prefix: Optional test prefix for isolation
            **kwargs: Additional monitoring parameters
            
        Returns:
            Monitoring session ID
        """
        monitoring_id = f"monitor_{uuid.uuid4().hex[:8]}"
        
        # Convert string to enum if needed
        if isinstance(monitoring_type, str):
            try:
                monitor_type_enum = MonitoringType(monitoring_type)
            except ValueError:
                monitor_type_enum = MonitoringType.GENERAL
        else:
            monitor_type_enum = monitoring_type
        
        metrics = PerformanceMetrics(
            monitoring_id=monitoring_id,
            monitoring_type=monitor_type_enum,
            start_time=time.time(),
            test_prefix=test_prefix
        )
        
        # Initialize monitoring-specific metrics
        if monitor_type_enum == MonitoringType.CONNECTION_POOL:
            metrics.metrics.update({
                "initial_connections": 0,
                "peak_connections": 0,
                "connection_waits": 0,
                "connection_timeouts": 0
            })
        elif monitor_type_enum == MonitoringType.QUERY_PERFORMANCE:
            metrics.metrics.update({
                "queries_executed": 0,
                "total_query_time": 0.0,
                "slow_queries": 0,
                "query_errors": 0
            })
        elif monitor_type_enum == MonitoringType.TRANSACTION_PERFORMANCE:
            metrics.metrics.update({
                "transactions_started": 0,
                "transactions_committed": 0,
                "transactions_rolled_back": 0,
                "deadlocks": 0
            })
        
        self._active_monitors[monitoring_id] = metrics
        
        logger.info(f"Started {monitoring_type} monitoring session: {monitoring_id}")
        return monitoring_id
    
    async def stop_monitoring(self, monitoring_id: str) -> Dict[str, Any]:
        """
        Stop monitoring session and return collected metrics.
        
        Args:
            monitoring_id: Monitoring session ID to stop
            
        Returns:
            Dictionary containing performance metrics
            
        Raises:
            ValueError: If monitoring_id not found
        """
        if monitoring_id not in self._active_monitors:
            raise ValueError(f"No active monitoring session found for ID: {monitoring_id}")
        
        metrics = self._active_monitors.pop(monitoring_id)
        metrics.end_time = time.time()
        metrics.duration_seconds = metrics.end_time - metrics.start_time
        
        # Generate summary statistics based on monitoring type
        summary_stats = self._generate_summary_stats(metrics)
        
        # Store completed monitoring session
        self._completed_monitors[monitoring_id] = metrics
        
        logger.info(f"Stopped monitoring session {monitoring_id} after {metrics.duration_seconds:.2f}s")
        
        return {
            "monitoring_id": monitoring_id,
            "monitoring_type": metrics.monitoring_type.value,
            "duration_seconds": metrics.duration_seconds,
            "test_prefix": metrics.test_prefix,
            "metrics": metrics.metrics,
            "summary": summary_stats
        }
    
    def _generate_summary_stats(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Generate summary statistics for monitoring session."""
        summary = {
            "status": "completed",
            "duration_seconds": metrics.duration_seconds,
            "performance_rating": "good"  # Default rating
        }
        
        if metrics.monitoring_type == MonitoringType.CONNECTION_POOL:
            peak_connections = metrics.metrics.get("peak_connections", 0)
            connection_timeouts = metrics.metrics.get("connection_timeouts", 0)
            
            summary.update({
                "peak_connections_used": peak_connections,
                "connection_efficiency": "high" if connection_timeouts == 0 else "low",
                "pool_pressure": "low" if peak_connections < 30 else "high"
            })
            
        elif metrics.monitoring_type == MonitoringType.QUERY_PERFORMANCE:
            queries_executed = metrics.metrics.get("queries_executed", 0)
            slow_queries = metrics.metrics.get("slow_queries", 0)
            
            if queries_executed > 0:
                slow_query_percentage = (slow_queries / queries_executed) * 100
                avg_query_time = metrics.metrics.get("total_query_time", 0) / queries_executed
            else:
                slow_query_percentage = 0
                avg_query_time = 0
            
            summary.update({
                "queries_executed": queries_executed,
                "average_query_time_ms": avg_query_time * 1000,
                "slow_query_percentage": slow_query_percentage,
                "query_efficiency": "high" if slow_query_percentage < 5 else "low"
            })
        
        return summary
    
    async def record_metric(self, monitoring_id: str, metric_name: str, value: Any) -> None:
        """
        Record a metric for an active monitoring session.
        
        Args:
            monitoring_id: Active monitoring session ID
            metric_name: Name of the metric to record
            value: Metric value
        """
        if monitoring_id in self._active_monitors:
            self._active_monitors[monitoring_id].metrics[metric_name] = value
            logger.debug(f"Recorded metric {metric_name}={value} for session {monitoring_id}")
    
    async def increment_metric(self, monitoring_id: str, metric_name: str, increment: float = 1.0) -> None:
        """
        Increment a numeric metric for an active monitoring session.
        
        Args:
            monitoring_id: Active monitoring session ID
            metric_name: Name of the metric to increment
            increment: Amount to increment (default 1.0)
        """
        if monitoring_id in self._active_monitors:
            current_value = self._active_monitors[monitoring_id].metrics.get(metric_name, 0)
            self._active_monitors[monitoring_id].metrics[metric_name] = current_value + increment
            logger.debug(f"Incremented metric {metric_name} by {increment} for session {monitoring_id}")
    
    def get_active_monitors(self) -> List[str]:
        """Get list of active monitoring session IDs."""
        return list(self._active_monitors.keys())
    
    def get_completed_monitors(self) -> List[str]:
        """Get list of completed monitoring session IDs."""
        return list(self._completed_monitors.keys())
    
    async def cleanup(self) -> None:
        """Clean up monitoring resources."""
        # Stop any active monitors
        active_ids = list(self._active_monitors.keys())
        for monitoring_id in active_ids:
            try:
                await self.stop_monitoring(monitoring_id)
            except Exception as e:
                logger.warning(f"Error stopping monitor {monitoring_id} during cleanup: {e}")
        
        # Clear completed monitors
        self._completed_monitors.clear()
        
        logger.info("Database Performance Monitor cleaned up")


# Export for import compatibility
__all__ = [
    'DatabasePerformanceMonitor',
    'MonitoringType',
    'PerformanceMetrics'
]