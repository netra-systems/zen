"""
Enhanced Connection Pool Monitor for Issue #1278

CRITICAL PURPOSE: Monitor database connection pool health and performance
to detect infrastructure issues early and support circuit breaker decisions.

Business Impact: Prevents connection pool exhaustion and provides early
warning of infrastructure degradation affecting $500K+ ARR platform.

Issue #1278 Focus:
- VPC connector capacity monitoring
- Cloud SQL connection timeout tracking
- Connection pool exhaustion prevention
- Infrastructure failure correlation
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import statistics
from collections import deque

from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.pool import Pool, QueuePool, NullPool, StaticPool
from sqlalchemy import text

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class PoolHealthStatus(Enum):
    """Connection pool health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    FAILED = "failed"


class ConnectionIssueType(Enum):
    """Types of connection issues for Issue #1278."""
    POOL_EXHAUSTION = "pool_exhaustion"
    VPC_CONNECTIVITY = "vpc_connectivity"
    CLOUD_SQL_TIMEOUT = "cloud_sql_timeout"
    CONNECTION_LEAK = "connection_leak"
    SLOW_CONNECTIONS = "slow_connections"
    SSL_HANDSHAKE_FAILURE = "ssl_handshake_failure"
    AUTHENTICATION_FAILURE = "authentication_failure"


@dataclass
class PoolMetrics:
    """Comprehensive connection pool metrics."""
    # Basic pool metrics
    pool_size: int = 0
    checked_out_connections: int = 0
    overflow_connections: int = 0
    invalidated_connections: int = 0
    
    # Performance metrics
    connection_acquisition_times: deque = field(default_factory=lambda: deque(maxlen=100))
    query_execution_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Health tracking
    successful_connections: int = 0
    failed_connections: int = 0
    connection_timeouts: int = 0
    
    # Infrastructure-specific metrics (Issue #1278)
    vpc_connector_failures: int = 0
    cloud_sql_timeouts: int = 0
    ssl_handshake_failures: int = 0
    
    # Timing
    last_health_check: Optional[datetime] = None
    last_connection_success: Optional[datetime] = None
    last_connection_failure: Optional[datetime] = None
    
    # Trend analysis
    connection_failure_rate_5m: float = 0.0
    avg_connection_time_5m: float = 0.0
    
    def add_connection_time(self, duration_ms: float):
        """Add connection acquisition time."""
        self.connection_acquisition_times.append(duration_ms)
    
    def add_query_time(self, duration_ms: float):
        """Add query execution time."""
        self.query_execution_times.append(duration_ms)
    
    def get_avg_connection_time(self) -> float:
        """Get average connection acquisition time."""
        return statistics.mean(self.connection_acquisition_times) if self.connection_acquisition_times else 0.0
    
    def get_avg_query_time(self) -> float:
        """Get average query execution time."""
        return statistics.mean(self.query_execution_times) if self.query_execution_times else 0.0
    
    def get_connection_failure_rate(self) -> float:
        """Get connection failure rate percentage."""
        total = self.successful_connections + self.failed_connections
        return (self.failed_connections / total * 100) if total > 0 else 0.0


@dataclass
class PoolConfiguration:
    """Connection pool configuration tracking."""
    pool_type: str
    pool_size: int
    max_overflow: int
    pool_timeout: float
    pool_recycle: int
    pool_pre_ping: bool
    
    # Issue #1278 specific configuration
    vpc_connector_timeout: float = 600.0
    cloud_sql_timeout: float = 600.0
    ssl_timeout: float = 30.0


class ConnectionPoolMonitor:
    """Enhanced connection pool monitor with Issue #1278 infrastructure awareness."""
    
    def __init__(self, name: str, engine: Union[Engine, AsyncEngine]):
        """Initialize connection pool monitor."""
        self.name = name
        self.engine = engine
        self.pool = engine.pool if hasattr(engine, 'pool') else None
        self.metrics = PoolMetrics()
        self.config = self._extract_pool_config()
        
        # Health thresholds
        self.high_utilization_threshold = 0.8  # 80% pool utilization
        self.critical_utilization_threshold = 0.95  # 95% pool utilization
        self.slow_connection_threshold = 5000.0  # 5 seconds
        self.critical_connection_threshold = 30000.0  # 30 seconds
        
        # Monitoring state
        self.monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Issue tracking
        self.recent_issues: deque = deque(maxlen=50)

    def _extract_pool_config(self) -> PoolConfiguration:
        """Extract current pool configuration."""
        if not self.pool:
            return PoolConfiguration(
                pool_type="unknown",
                pool_size=0,
                max_overflow=0,
                pool_timeout=30.0,
                pool_recycle=-1,
                pool_pre_ping=False
            )
        
        pool_type = type(self.pool).__name__
        
        return PoolConfiguration(
            pool_type=pool_type,
            pool_size=getattr(self.pool, '_pool_size', 0),
            max_overflow=getattr(self.pool, '_max_overflow', 0),
            pool_timeout=getattr(self.pool, '_timeout', 30.0),
            pool_recycle=getattr(self.pool, '_recycle', -1),
            pool_pre_ping=getattr(self.pool, '_pre_ping', False)
        )

    async def check_pool_health(self) -> Dict[str, Any]:
        """Perform comprehensive pool health check."""
        start_time = time.time()
        
        health_result = {
            "name": self.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": PoolHealthStatus.HEALTHY.value,
            "issues": [],
            "metrics": {},
            "recommendations": []
        }
        
        try:
            # Update basic pool metrics
            await self._update_pool_metrics()
            
            # Test connection acquisition
            connection_time = await self._test_connection_acquisition()
            if connection_time:
                self.metrics.add_connection_time(connection_time)
            
            # Analyze pool health
            health_status, issues = self._analyze_pool_health()
            health_result["status"] = health_status.value
            health_result["issues"] = issues
            
            # Update metrics in result
            health_result["metrics"] = {
                "pool_size": self.metrics.pool_size,
                "checked_out": self.metrics.checked_out_connections,
                "overflow": self.metrics.overflow_connections,
                "utilization_percent": self._calculate_utilization(),
                "avg_connection_time_ms": round(self.metrics.get_avg_connection_time(), 2),
                "avg_query_time_ms": round(self.metrics.get_avg_query_time(), 2),
                "failure_rate_percent": round(self.metrics.get_connection_failure_rate(), 2),
                "successful_connections": self.metrics.successful_connections,
                "failed_connections": self.metrics.failed_connections,
                "connection_timeouts": self.metrics.connection_timeouts
            }
            
            # Infrastructure-specific metrics for Issue #1278
            health_result["infrastructure_metrics"] = {
                "vpc_connector_failures": self.metrics.vpc_connector_failures,
                "cloud_sql_timeouts": self.metrics.cloud_sql_timeouts,
                "ssl_handshake_failures": self.metrics.ssl_handshake_failures
            }
            
            # Generate recommendations
            health_result["recommendations"] = self._generate_recommendations(health_status, issues)
            
            self.metrics.last_health_check = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Pool health check failed for '{self.name}': {e}")
            health_result["status"] = PoolHealthStatus.FAILED.value
            health_result["issues"].append({
                "type": "health_check_failure",
                "severity": "critical",
                "description": f"Health check failed: {str(e)}"
            })
        
        check_duration = (time.time() - start_time) * 1000
        health_result["health_check_duration_ms"] = round(check_duration, 2)
        
        return health_result

    async def _update_pool_metrics(self):
        """Update basic pool metrics from SQLAlchemy pool."""
        if not self.pool:
            return
        
        try:
            # Get current pool status
            self.metrics.pool_size = getattr(self.pool, 'size', 0)
            self.metrics.checked_out_connections = getattr(self.pool, 'checkedout', 0)
            self.metrics.overflow_connections = getattr(self.pool, 'overflow', 0)
            self.metrics.invalidated_connections = getattr(self.pool, 'invalidated', 0)
            
        except Exception as e:
            logger.warning(f"Failed to update pool metrics for '{self.name}': {e}")

    async def _test_connection_acquisition(self) -> Optional[float]:
        """Test connection acquisition time."""
        start_time = time.time()
        
        try:
            # For async engines, use async connection
            if hasattr(self.engine, 'begin'):
                async with self.engine.begin() as conn:
                    # Simple health check query
                    await conn.execute(text("SELECT 1"))
            else:
                # For sync engines
                with self.engine.begin() as conn:
                    conn.execute(text("SELECT 1"))
            
            acquisition_time = (time.time() - start_time) * 1000
            self.metrics.successful_connections += 1
            self.metrics.last_connection_success = datetime.now(timezone.utc)
            
            return acquisition_time
            
        except asyncio.TimeoutError:
            self.metrics.connection_timeouts += 1
            self.metrics.cloud_sql_timeouts += 1
            self.metrics.failed_connections += 1
            self.metrics.last_connection_failure = datetime.now(timezone.utc)
            
            self._record_issue(ConnectionIssueType.CLOUD_SQL_TIMEOUT, "critical", "Connection acquisition timed out")
            return None
            
        except Exception as e:
            self.metrics.failed_connections += 1
            self.metrics.last_connection_failure = datetime.now(timezone.utc)
            
            # Classify the error for Issue #1278
            issue_type = self._classify_connection_error(e)
            self._record_issue(issue_type, "high", f"Connection failed: {str(e)}")
            
            return None

    def _classify_connection_error(self, error: Exception) -> ConnectionIssueType:
        """Classify connection error for Issue #1278 analysis."""
        error_str = str(error).lower()
        
        if any(pattern in error_str for pattern in [
            'connection refused', 'network unreachable', 'vpc connector'
        ]):
            self.metrics.vpc_connector_failures += 1
            return ConnectionIssueType.VPC_CONNECTIVITY
        
        elif any(pattern in error_str for pattern in [
            'timeout', 'timed out'
        ]):
            self.metrics.cloud_sql_timeouts += 1
            return ConnectionIssueType.CLOUD_SQL_TIMEOUT
        
        elif any(pattern in error_str for pattern in [
            'ssl', 'certificate', 'handshake'
        ]):
            self.metrics.ssl_handshake_failures += 1
            return ConnectionIssueType.SSL_HANDSHAKE_FAILURE
        
        elif any(pattern in error_str for pattern in [
            'pool', 'too many connections'
        ]):
            return ConnectionIssueType.POOL_EXHAUSTION
        
        elif any(pattern in error_str for pattern in [
            'authentication', 'password', 'credentials'
        ]):
            return ConnectionIssueType.AUTHENTICATION_FAILURE
        
        else:
            return ConnectionIssueType.SLOW_CONNECTIONS

    def _analyze_pool_health(self) -> tuple[PoolHealthStatus, List[Dict[str, Any]]]:
        """Analyze pool health and identify issues."""
        issues = []
        
        # Check utilization
        utilization = self._calculate_utilization()
        
        if utilization >= self.critical_utilization_threshold:
            issues.append({
                "type": ConnectionIssueType.POOL_EXHAUSTION.value,
                "severity": "critical",
                "description": f"Pool utilization critical: {utilization:.1%}",
                "current_value": f"{utilization:.1%}",
                "threshold": f"{self.critical_utilization_threshold:.1%}"
            })
        elif utilization >= self.high_utilization_threshold:
            issues.append({
                "type": ConnectionIssueType.POOL_EXHAUSTION.value,
                "severity": "high",
                "description": f"Pool utilization high: {utilization:.1%}",
                "current_value": f"{utilization:.1%}",
                "threshold": f"{self.high_utilization_threshold:.1%}"
            })
        
        # Check connection times
        avg_connection_time = self.metrics.get_avg_connection_time()
        if avg_connection_time > self.critical_connection_threshold:
            issues.append({
                "type": ConnectionIssueType.SLOW_CONNECTIONS.value,
                "severity": "critical",
                "description": f"Critical connection time: {avg_connection_time:.0f}ms",
                "current_value": f"{avg_connection_time:.0f}ms",
                "threshold": f"{self.critical_connection_threshold:.0f}ms"
            })
        elif avg_connection_time > self.slow_connection_threshold:
            issues.append({
                "type": ConnectionIssueType.SLOW_CONNECTIONS.value,
                "severity": "medium",
                "description": f"Slow connection time: {avg_connection_time:.0f}ms",
                "current_value": f"{avg_connection_time:.0f}ms",
                "threshold": f"{self.slow_connection_threshold:.0f}ms"
            })
        
        # Check failure rate
        failure_rate = self.metrics.get_connection_failure_rate()
        if failure_rate > 20.0:  # 20% failure rate is critical
            issues.append({
                "type": ConnectionIssueType.VPC_CONNECTIVITY.value,
                "severity": "critical",
                "description": f"High connection failure rate: {failure_rate:.1f}%",
                "current_value": f"{failure_rate:.1f}%",
                "threshold": "20%"
            })
        elif failure_rate > 5.0:  # 5% failure rate is concerning
            issues.append({
                "type": ConnectionIssueType.VPC_CONNECTIVITY.value,
                "severity": "high",
                "description": f"Elevated connection failure rate: {failure_rate:.1f}%",
                "current_value": f"{failure_rate:.1f}%",
                "threshold": "5%"
            })
        
        # Check for infrastructure-specific issues
        if self.metrics.vpc_connector_failures > 0:
            issues.append({
                "type": ConnectionIssueType.VPC_CONNECTIVITY.value,
                "severity": "high",
                "description": f"VPC connector failures detected: {self.metrics.vpc_connector_failures}",
                "remediation": "Check VPC connector configuration and capacity"
            })
        
        if self.metrics.cloud_sql_timeouts > 0:
            issues.append({
                "type": ConnectionIssueType.CLOUD_SQL_TIMEOUT.value,
                "severity": "high",
                "description": f"Cloud SQL timeouts detected: {self.metrics.cloud_sql_timeouts}",
                "remediation": "Increase timeout settings and check Cloud SQL performance"
            })
        
        # Determine overall health status
        if any(issue["severity"] == "critical" for issue in issues):
            status = PoolHealthStatus.CRITICAL
        elif any(issue["severity"] == "high" for issue in issues):
            status = PoolHealthStatus.DEGRADED
        elif len(issues) > 0:
            status = PoolHealthStatus.DEGRADED
        else:
            status = PoolHealthStatus.HEALTHY
        
        return status, issues

    def _calculate_utilization(self) -> float:
        """Calculate pool utilization percentage."""
        if self.metrics.pool_size == 0:
            return 0.0
        
        total_connections = self.metrics.checked_out_connections + self.metrics.overflow_connections
        return total_connections / (self.metrics.pool_size + self.config.max_overflow)

    def _record_issue(self, issue_type: ConnectionIssueType, severity: str, description: str):
        """Record a connection issue for tracking."""
        issue = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": issue_type.value,
            "severity": severity,
            "description": description
        }
        self.recent_issues.append(issue)

    def _generate_recommendations(self, health_status: PoolHealthStatus, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on health analysis."""
        recommendations = []
        
        # High utilization recommendations
        utilization = self._calculate_utilization()
        if utilization > self.high_utilization_threshold:
            recommendations.append(f"Consider increasing pool size (current: {self.config.pool_size})")
            recommendations.append("Monitor for connection leaks in application code")
            recommendations.append("Review connection usage patterns")
        
        # Slow connection recommendations
        avg_time = self.metrics.get_avg_connection_time()
        if avg_time > self.slow_connection_threshold:
            recommendations.append("Investigate network latency to database")
            recommendations.append("Check VPC connector capacity and configuration")
            recommendations.append("Consider connection pooling optimization")
        
        # Infrastructure-specific recommendations for Issue #1278
        if self.metrics.vpc_connector_failures > 0:
            recommendations.append("Review VPC connector configuration in Cloud Run")
            recommendations.append("Check VPC connector capacity limits")
            recommendations.append("Validate private IP connectivity to Cloud SQL")
        
        if self.metrics.cloud_sql_timeouts > 0:
            recommendations.append("Increase database timeout settings to 600+ seconds")
            recommendations.append("Check Cloud SQL instance performance metrics")
            recommendations.append("Consider Cloud SQL instance scaling")
        
        if self.metrics.ssl_handshake_failures > 0:
            recommendations.append("Check SSL certificate validity")
            recommendations.append("Review SSL configuration for Cloud SQL")
            recommendations.append("Validate TLS version compatibility")
        
        # Failure rate recommendations
        failure_rate = self.metrics.get_connection_failure_rate()
        if failure_rate > 5.0:
            recommendations.append("Implement connection retry logic with exponential backoff")
            recommendations.append("Enable connection pre-ping validation")
            recommendations.append("Review database connectivity from application environment")
        
        return recommendations

    async def start_monitoring(self, interval_seconds: int = 60):
        """Start continuous pool monitoring."""
        if self.monitoring_active:
            logger.warning(f"Monitoring already active for pool '{self.name}'")
            return
        
        self.monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop(interval_seconds))
        logger.info(f"Started continuous monitoring for pool '{self.name}' (interval: {interval_seconds}s)")

    async def stop_monitoring(self):
        """Stop continuous monitoring."""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Stopped monitoring for pool '{self.name}'")

    async def _monitoring_loop(self, interval_seconds: int):
        """Continuous monitoring loop."""
        while self.monitoring_active:
            try:
                health_result = await self.check_pool_health()
                
                # Log critical issues
                if health_result["status"] == PoolHealthStatus.CRITICAL.value:
                    logger.critical(f"Pool '{self.name}' health CRITICAL: {len(health_result['issues'])} issues")
                    for issue in health_result["issues"]:
                        if issue.get("severity") == "critical":
                            logger.critical(f"  • {issue['description']}")
                
                elif health_result["status"] == PoolHealthStatus.DEGRADED.value:
                    logger.warning(f"Pool '{self.name}' health DEGRADED: {len(health_result['issues'])} issues")
                
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop for pool '{self.name}': {e}")
                await asyncio.sleep(interval_seconds)

    def get_summary_report(self) -> Dict[str, Any]:
        """Get comprehensive summary report."""
        return {
            "name": self.name,
            "health_status": self._analyze_pool_health()[0].value,
            "configuration": {
                "pool_type": self.config.pool_type,
                "pool_size": self.config.pool_size,
                "max_overflow": self.config.max_overflow,
                "pool_timeout": self.config.pool_timeout,
                "pool_recycle": self.config.pool_recycle,
                "pre_ping": self.config.pool_pre_ping
            },
            "current_metrics": {
                "utilization_percent": round(self._calculate_utilization() * 100, 1),
                "avg_connection_time_ms": round(self.metrics.get_avg_connection_time(), 2),
                "failure_rate_percent": round(self.metrics.get_connection_failure_rate(), 2),
                "total_connections": self.metrics.successful_connections + self.metrics.failed_connections,
                "recent_failures": len([issue for issue in self.recent_issues 
                                      if datetime.fromisoformat(issue["timestamp"]) > 
                                      datetime.now(timezone.utc) - timedelta(minutes=15)])
            },
            "infrastructure_health": {
                "vpc_connector_issues": self.metrics.vpc_connector_failures,
                "cloud_sql_timeouts": self.metrics.cloud_sql_timeouts,
                "ssl_handshake_failures": self.metrics.ssl_handshake_failures
            },
            "recommendations": self._generate_recommendations(*self._analyze_pool_health()),
            "last_health_check": self.metrics.last_health_check.isoformat() if self.metrics.last_health_check else None,
            "monitoring_active": self.monitoring_active
        }


# Global pool monitor registry
_pool_monitors: Dict[str, ConnectionPoolMonitor] = {}


def register_pool_monitor(name: str, engine: Union[Engine, AsyncEngine]) -> ConnectionPoolMonitor:
    """Register a connection pool monitor."""
    monitor = ConnectionPoolMonitor(name, engine)
    _pool_monitors[name] = monitor
    logger.info(f"Registered connection pool monitor for '{name}'")
    return monitor


def get_pool_monitor(name: str) -> Optional[ConnectionPoolMonitor]:
    """Get a registered pool monitor."""
    return _pool_monitors.get(name)


def get_all_pool_monitors() -> Dict[str, ConnectionPoolMonitor]:
    """Get all registered pool monitors."""
    return _pool_monitors.copy()


async def get_all_pools_health() -> Dict[str, Any]:
    """Get health status of all monitored pools."""
    health_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_pools": len(_pool_monitors),
        "pools": {},
        "summary": {
            "healthy": 0,
            "degraded": 0,
            "critical": 0,
            "failed": 0,
            "total_issues": 0
        }
    }
    
    for name, monitor in _pool_monitors.items():
        pool_health = await monitor.check_pool_health()
        health_report["pools"][name] = pool_health
        
        # Update summary
        status = pool_health["status"]
        if status == PoolHealthStatus.HEALTHY.value:
            health_report["summary"]["healthy"] += 1
        elif status == PoolHealthStatus.DEGRADED.value:
            health_report["summary"]["degraded"] += 1
        elif status == PoolHealthStatus.CRITICAL.value:
            health_report["summary"]["critical"] += 1
        else:
            health_report["summary"]["failed"] += 1
        
        health_report["summary"]["total_issues"] += len(pool_health.get("issues", []))
    
    return health_report