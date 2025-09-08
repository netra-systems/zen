"""Database Connection Pool Monitoring

Provides real-time monitoring and health checks for database connection pools.
Helps prevent 500 errors by detecting pool exhaustion and connection issues early.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from sqlalchemy import create_engine, pool, event
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import Pool

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class PoolMetrics:
    """Metrics for database connection pool monitoring."""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    overflow_connections: int = 0
    checked_out_connections: int = 0
    checked_in_connections: int = 0
    connection_errors: int = 0
    pool_timeouts: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    health_status: str = "healthy"
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for logging/monitoring."""
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "overflow_connections": self.overflow_connections,
            "checked_out_connections": self.checked_out_connections,
            "checked_in_connections": self.checked_in_connections,
            "connection_errors": self.connection_errors,
            "pool_timeouts": self.pool_timeouts,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "health_status": self.health_status,
            "warnings": self.warnings
        }


class ConnectionPoolMonitor:
    """
    Monitors database connection pool health and performance.
    
    Features:
    - Real-time pool metrics tracking
    - Automatic health checks
    - Early warning system for pool exhaustion
    - Connection leak detection
    - Performance metrics collection
    """
    
    def __init__(self, pool_name: str = "main"):
        """
        Initialize connection pool monitor.
        
        Args:
            pool_name: Name identifier for this pool
        """
        self.pool_name = pool_name
        self.metrics = PoolMetrics()
        self._monitored_pools: Dict[str, Pool] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_monitoring = False
        self._check_interval = 30  # seconds
        
        # Thresholds for health warnings
        self.warning_threshold = 0.75  # 75% pool usage triggers warning
        self.critical_threshold = 0.90  # 90% pool usage is critical
        
        logger.info(f"ConnectionPoolMonitor initialized for pool: {pool_name}")
    
    def attach_to_pool(self, engine: Any) -> None:
        """
        Attach monitoring to a database engine's connection pool.
        
        Args:
            engine: SQLAlchemy engine (sync or async)
        """
        try:
            # Get the actual pool object
            if hasattr(engine, 'pool'):
                pool_obj = engine.pool
            elif hasattr(engine, 'sync_engine') and hasattr(engine.sync_engine, 'pool'):
                pool_obj = engine.sync_engine.pool
            else:
                logger.warning(f"Could not find pool in engine: {type(engine)}")
                return
            
            # Register pool for monitoring
            pool_id = str(id(pool_obj))
            self._monitored_pools[pool_id] = pool_obj
            
            # Attach event listeners for pool events
            self._attach_pool_events(engine)
            
            logger.info(f"Attached monitoring to pool {pool_id} for {self.pool_name}")
            
        except Exception as e:
            logger.error(f"Failed to attach pool monitoring: {e}", exc_info=True)
    
    def _attach_pool_events(self, engine: Any) -> None:
        """Attach event listeners to track pool events."""
        try:
            # Track connection checkout
            @event.listens_for(engine, "checkout", named=True)
            def receive_checkout(**kw):
                self.metrics.checked_out_connections += 1
                self._update_pool_metrics()
            
            # Track connection checkin
            @event.listens_for(engine, "checkin", named=True)
            def receive_checkin(**kw):
                self.metrics.checked_in_connections += 1
                self._update_pool_metrics()
            
            # Track connection errors
            @event.listens_for(engine, "connect", named=True)
            def receive_connect(**kw):
                self.metrics.total_connections += 1
            
            logger.debug(f"Pool events attached for {self.pool_name}")
            
        except Exception as e:
            logger.warning(f"Could not attach all pool events: {e}")
    
    def _update_pool_metrics(self) -> None:
        """Update current pool metrics from monitored pools."""
        try:
            total_size = 0
            total_checked_out = 0
            total_overflow = 0
            
            for pool_id, pool_obj in self._monitored_pools.items():
                if hasattr(pool_obj, 'size'):
                    total_size += pool_obj.size()
                if hasattr(pool_obj, 'checked_out'):
                    total_checked_out += pool_obj.checked_out()
                if hasattr(pool_obj, 'overflow'):
                    total_overflow += pool_obj.overflow()
            
            # Update metrics
            self.metrics.total_connections = total_size
            self.metrics.active_connections = total_checked_out
            self.metrics.idle_connections = total_size - total_checked_out
            self.metrics.overflow_connections = total_overflow
            
            # Check health status
            self._check_pool_health()
            
        except Exception as e:
            logger.error(f"Error updating pool metrics: {e}")
            self.metrics.connection_errors += 1
            self.metrics.last_error = str(e)
            self.metrics.last_error_time = datetime.utcnow()
    
    def _check_pool_health(self) -> None:
        """Check pool health and update status."""
        self.metrics.warnings.clear()
        
        if self.metrics.total_connections == 0:
            self.metrics.health_status = "unknown"
            return
        
        # Calculate pool usage percentage
        usage = self.metrics.active_connections / self.metrics.total_connections
        
        if usage >= self.critical_threshold:
            self.metrics.health_status = "critical"
            self.metrics.warnings.append(
                f"Pool usage critical: {usage:.1%} of connections in use"
            )
            logger.critical(
                f"DATABASE POOL CRITICAL: {self.pool_name} at {usage:.1%} capacity "
                f"({self.metrics.active_connections}/{self.metrics.total_connections})"
            )
            
        elif usage >= self.warning_threshold:
            self.metrics.health_status = "warning"
            self.metrics.warnings.append(
                f"Pool usage high: {usage:.1%} of connections in use"
            )
            logger.warning(
                f"Database pool warning: {self.pool_name} at {usage:.1%} capacity"
            )
            
        else:
            self.metrics.health_status = "healthy"
        
        # Check for connection leaks (connections checked out for too long)
        if self.metrics.checked_out_connections - self.metrics.checked_in_connections > 10:
            self.metrics.warnings.append(
                "Possible connection leak detected: many unchecked connections"
            )
        
        # Check for excessive errors
        if self.metrics.connection_errors > 5:
            self.metrics.warnings.append(
                f"High error rate: {self.metrics.connection_errors} connection errors"
            )
    
    async def start_monitoring(self) -> None:
        """Start background monitoring task."""
        if self._is_monitoring:
            logger.warning(f"Monitoring already active for {self.pool_name}")
            return
        
        self._is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Started monitoring for pool {self.pool_name}")
    
    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._is_monitoring:
            try:
                # Update metrics
                self._update_pool_metrics()
                
                # Log current status
                if self.metrics.health_status != "healthy":
                    logger.warning(
                        f"Pool {self.pool_name} status: {self.metrics.health_status}",
                        extra={"metrics": self.metrics.to_dict()}
                    )
                else:
                    logger.debug(
                        f"Pool {self.pool_name} healthy",
                        extra={"metrics": self.metrics.to_dict()}
                    )
                
                # Wait for next check
                await asyncio.sleep(self._check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self._check_interval)
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring task."""
        self._is_monitoring = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Stopped monitoring for pool {self.pool_name}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current pool metrics."""
        self._update_pool_metrics()
        return self.metrics.to_dict()
    
    def is_healthy(self) -> bool:
        """Check if pool is healthy."""
        return self.metrics.health_status == "healthy"
    
    def get_warnings(self) -> List[str]:
        """Get current warning messages."""
        return self.metrics.warnings.copy()


# Global monitor instance
_pool_monitor: Optional[ConnectionPoolMonitor] = None


def get_pool_monitor() -> ConnectionPoolMonitor:
    """Get or create global pool monitor instance."""
    global _pool_monitor
    if _pool_monitor is None:
        _pool_monitor = ConnectionPoolMonitor()
    return _pool_monitor


async def setup_pool_monitoring(engine: Any) -> None:
    """
    Setup connection pool monitoring for an engine.
    
    Args:
        engine: SQLAlchemy engine to monitor
    """
    monitor = get_pool_monitor()
    monitor.attach_to_pool(engine)
    await monitor.start_monitoring()
    logger.info("Database connection pool monitoring activated")


async def get_pool_health() -> Dict[str, Any]:
    """Get current pool health status."""
    monitor = get_pool_monitor()
    return {
        "pool_name": monitor.pool_name,
        "health_status": monitor.metrics.health_status,
        "metrics": monitor.get_metrics(),
        "warnings": monitor.get_warnings(),
        "timestamp": datetime.utcnow().isoformat()
    }