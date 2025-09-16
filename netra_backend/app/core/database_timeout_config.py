"""
Database Timeout Configuration - Environment-Aware Timeout Settings

This module provides environment-specific database timeout configurations
to handle different connection requirements for local development vs. Cloud SQL.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Staging Environment Stability
- Value Impact: Ensures database connections work reliably across all environments
- Strategic Impact: Prevents staging deployment failures and enables reliable CI/CD
"""

from typing import Dict, Optional, Callable, Any
import logging
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class ConnectionMetrics:
    """Container for database connection performance metrics."""
    connection_attempts: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    total_connection_time: float = 0.0
    max_connection_time: float = 0.0
    min_connection_time: float = float('inf')
    last_connection_time: Optional[float] = None
    timeout_violations: int = 0
    recent_connection_times: deque = field(default_factory=lambda: deque(maxlen=100))
    first_recorded: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def add_connection_attempt(self, connection_time: float, success: bool, timeout_threshold: float) -> None:
        """Record a new connection attempt with timing and success status."""
        now = datetime.now()
        if self.first_recorded is None:
            self.first_recorded = now
        self.last_updated = now

        self.connection_attempts += 1
        self.last_connection_time = connection_time
        self.recent_connection_times.append(connection_time)
        self.total_connection_time += connection_time

        if connection_time > self.max_connection_time:
            self.max_connection_time = connection_time
        if connection_time < self.min_connection_time:
            self.min_connection_time = connection_time

        if success:
            self.successful_connections += 1
        else:
            self.failed_connections += 1

        if connection_time > timeout_threshold:
            self.timeout_violations += 1

    def get_average_connection_time(self) -> float:
        """Calculate average connection time across all attempts."""
        if self.connection_attempts == 0:
            return 0.0
        return self.total_connection_time / self.connection_attempts

    def get_recent_average_connection_time(self, window_size: int = 20) -> float:
        """Calculate average connection time for recent attempts."""
        if not self.recent_connection_times:
            return 0.0
        recent = list(self.recent_connection_times)[-window_size:]
        return sum(recent) / len(recent)

    def get_success_rate(self) -> float:
        """Calculate connection success rate as percentage."""
        if self.connection_attempts == 0:
            return 0.0
        return (self.successful_connections / self.connection_attempts) * 100.0

    def get_timeout_violation_rate(self) -> float:
        """Calculate timeout violation rate as percentage."""
        if self.connection_attempts == 0:
            return 0.0
        return (self.timeout_violations / self.connection_attempts) * 100.0


class DatabaseConnectionMonitor:
    """Monitor and track database connection performance across environments."""

    def __init__(self):
        self._metrics_by_environment: Dict[str, ConnectionMetrics] = {}
        self._lock = threading.Lock()
        self._alert_callbacks: list[Callable[[str, Dict[str, Any]], None]] = []

    def register_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Register a callback function for connection performance alerts."""
        self._alert_callbacks.append(callback)

    def record_connection_attempt(self, environment: str, connection_time: float,
                                success: bool, timeout_config: Dict[str, float]) -> None:
        """Record a database connection attempt with timing and outcome."""
        with self._lock:
            if environment not in self._metrics_by_environment:
                self._metrics_by_environment[environment] = ConnectionMetrics()

            metrics = self._metrics_by_environment[environment]
            timeout_threshold = timeout_config.get('connection_timeout', 30.0)

            metrics.add_connection_attempt(connection_time, success, timeout_threshold)

            # Check for alert conditions
            self._check_alert_conditions(environment, metrics, timeout_config)

    def _check_alert_conditions(self, environment: str, metrics: ConnectionMetrics,
                               timeout_config: Dict[str, float]) -> None:
        """Check if current metrics warrant performance alerts."""
        alerts = []

        # Alert on high connection times (>80% of timeout threshold)
        connection_timeout = timeout_config.get('connection_timeout', 30.0)
        warning_threshold = connection_timeout * 0.8  # 80% of timeout
        critical_threshold = connection_timeout * 0.95  # 95% of timeout

        if metrics.last_connection_time:
            if metrics.last_connection_time > critical_threshold:
                alerts.append({
                    'level': 'critical',
                    'type': 'connection_time',
                    'message': f'Connection time {metrics.last_connection_time:.2f}s exceeds critical threshold {critical_threshold:.2f}s',
                    'value': metrics.last_connection_time,
                    'threshold': critical_threshold
                })
            elif metrics.last_connection_time > warning_threshold:
                alerts.append({
                    'level': 'warning',
                    'type': 'connection_time',
                    'message': f'Connection time {metrics.last_connection_time:.2f}s exceeds warning threshold {warning_threshold:.2f}s',
                    'value': metrics.last_connection_time,
                    'threshold': warning_threshold
                })

        # Alert on low success rate (if we have enough samples)
        if metrics.connection_attempts >= 10:
            success_rate = metrics.get_success_rate()
            if success_rate < 90.0:
                alerts.append({
                    'level': 'critical' if success_rate < 80.0 else 'warning',
                    'type': 'success_rate',
                    'message': f'Connection success rate {success_rate:.1f}% is below threshold',
                    'value': success_rate,
                    'threshold': 90.0
                })

        # Alert on timeout violation rate
        if metrics.connection_attempts >= 5:
            violation_rate = metrics.get_timeout_violation_rate()
            if violation_rate > 20.0:
                alerts.append({
                    'level': 'critical' if violation_rate > 40.0 else 'warning',
                    'type': 'timeout_violations',
                    'message': f'Timeout violation rate {violation_rate:.1f}% is above threshold',
                    'value': violation_rate,
                    'threshold': 20.0
                })

        # Fire alerts
        for alert in alerts:
            for callback in self._alert_callbacks:
                try:
                    callback(environment, alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")

    def get_environment_metrics(self, environment: str) -> Optional[ConnectionMetrics]:
        """Get connection metrics for a specific environment."""
        with self._lock:
            return self._metrics_by_environment.get(environment)

    def get_all_metrics(self) -> Dict[str, ConnectionMetrics]:
        """Get connection metrics for all environments."""
        with self._lock:
            return dict(self._metrics_by_environment)

    def get_performance_summary(self, environment: str) -> Dict[str, Any]:
        """Get a comprehensive performance summary for an environment."""
        metrics = self.get_environment_metrics(environment)
        if not metrics:
            return {'environment': environment, 'status': 'no_data'}

        return {
            'environment': environment,
            'connection_attempts': metrics.connection_attempts,
            'success_rate': metrics.get_success_rate(),
            'average_connection_time': metrics.get_average_connection_time(),
            'recent_average_connection_time': metrics.get_recent_average_connection_time(),
            'max_connection_time': metrics.max_connection_time,
            'min_connection_time': metrics.min_connection_time if metrics.min_connection_time != float('inf') else 0.0,
            'timeout_violation_rate': metrics.get_timeout_violation_rate(),
            'last_connection_time': metrics.last_connection_time,
            'monitoring_duration_hours': (
                (metrics.last_updated - metrics.first_recorded).total_seconds() / 3600
                if metrics.first_recorded and metrics.last_updated else 0
            ),
            'status': 'healthy' if metrics.get_success_rate() > 90 and metrics.get_timeout_violation_rate() < 10 else 'degraded'
        }

    def reset_metrics(self, environment: Optional[str] = None) -> None:
        """Reset metrics for specified environment or all environments."""
        with self._lock:
            if environment:
                if environment in self._metrics_by_environment:
                    del self._metrics_by_environment[environment]
            else:
                self._metrics_by_environment.clear()


# Global connection monitor instance
_connection_monitor = DatabaseConnectionMonitor()


def get_database_timeout_config(environment: str) -> Dict[str, float]:
    """Get database timeout configuration based on environment.
    
    Different environments have different connection characteristics:
    - Local development: Fast localhost connections
    - Test: Memory databases or fast local connections  
    - Staging: Cloud SQL requires more time for socket establishment
    - Production: Cloud SQL with high availability requirements
    
    Args:
        environment: Environment name (development, test, staging, production)
        
    Returns:
        Dictionary with timeout values in seconds
    """
    environment = environment.lower() if environment else "development"
    
    timeout_configs = {
        "development": {
            "initialization_timeout": 30.0,    # Local PostgreSQL is fast
            "table_setup_timeout": 15.0,       # Local database operations
            "connection_timeout": 20.0,        # Quick connection establishment
            "pool_timeout": 30.0,              # Connection pool operations
            "health_check_timeout": 10.0,      # Health check queries
        },
        "test": {
            "initialization_timeout": 25.0,    # Memory DB or test containers
            "table_setup_timeout": 10.0,       # Test operations should be fast
            "connection_timeout": 15.0,        # Test connections
            "pool_timeout": 20.0,              # Minimal pool operations
            "health_check_timeout": 5.0,       # Fast test health checks
        },
        "staging": {
            # CRITICAL FIX Issue #1278: VPC Connector Capacity Constraints - Further extended timeout configuration
            # Root cause analysis: Previous 45.0s still insufficient for compound infrastructure failures
            # New evidence from Issue #1278: VPC connector scaling + Cloud SQL capacity pressure creates compound delays
            # VPC connector capacity pressure: 30s delay during peak scaling events
            # Cloud SQL resource constraints: 25s delay under concurrent connection pressure
            # Network latency amplification: 10s additional delay during infrastructure stress
            # Safety margin for cascading failures: 15s buffer
            # PHASE 1 FIX: Extended timeouts based on test evidence from Issue #1278 Phase 1 remediation
            "initialization_timeout": 95.0,    # CRITICAL: Extended to handle compound VPC+CloudSQL delays (increased from 75.0)
            "table_setup_timeout": 25.0,       # Extended for schema operations under load (increased from 15.0)
            "connection_timeout": 45.0,        # Extended for VPC connector peak scaling delays (increased from 35.0)
            "pool_timeout": 60.0,              # Extended for connection pool exhaustion + VPC delays (increased from 45.0)
            "health_check_timeout": 30.0,      # Extended for compound infrastructure health checks (increased from 20.0)
        },
        "production": {
            # CRITICAL: Production needs maximum reliability
            "initialization_timeout": 90.0,    # High availability requirements
            "table_setup_timeout": 45.0,       # Production stability
            "connection_timeout": 60.0,        # Robust connection handling
            "pool_timeout": 70.0,              # Production connection pool
            "health_check_timeout": 30.0,      # Comprehensive health checks
        }
    }
    
    config = timeout_configs.get(environment, timeout_configs["development"])
    
    logger.debug(f"Database timeout configuration for {environment}: {config}")
    
    return config


def get_cloud_sql_optimized_config(environment: str) -> Dict[str, any]:
    """Get Cloud SQL specific configuration optimizations.
    
    Cloud SQL connections have different characteristics than TCP connections:
    - Uses Unix sockets (/cloudsql/...) instead of TCP
    - Requires specific connection parameters for optimal performance
    - Benefits from larger connection pools due to higher latency
    
    Args:
        environment: Environment name
        
    Returns:
        Dictionary with Cloud SQL specific configuration
    """
    if environment.lower() in ["staging", "production"]:
        return {
            # Connection arguments optimized for Cloud SQL
            "connect_args": {
                "server_settings": {
                    "application_name": f"netra_{environment}",
                    # Cloud SQL optimized keepalives
                    "tcp_keepalives_idle": "600",    # 10 minutes
                    "tcp_keepalives_interval": "30", # 30 seconds  
                    "tcp_keepalives_count": "3",     # 3 failed probes
                    # Connection optimization
                    "statement_timeout": "300000",   # 5 minutes for long operations
                    "idle_in_transaction_session_timeout": "300000",  # 5 minutes
                }
            },
            # Pool configuration for Cloud SQL with capacity constraints (Issue #1278)
            "pool_config": {
                "pool_size": 10,              # Reduced to respect Cloud SQL connection limits (reduced from 15)
                "max_overflow": 15,           # Reduced to stay within 80% of Cloud SQL capacity (reduced from 25)
                "pool_timeout": 90.0,         # Extended for VPC connector + Cloud SQL delays (already optimized at 90.0s)
                "pool_recycle": 3600,         # 1 hour recycle for stability
                "pool_pre_ping": True,        # Always verify connections
                "pool_reset_on_return": "rollback",  # Safe connection resets
                # New: VPC connector capacity awareness
                "vpc_connector_capacity_buffer": 5,   # Reserve connections for VPC connector scaling
                "cloud_sql_capacity_limit": 100,     # Track Cloud SQL instance connection limit
                "capacity_safety_margin": 0.8,       # Use only 80% of available connections
            }
        }
    else:
        # Development/test configuration
        return {
            "connect_args": {
                "server_settings": {
                    "application_name": f"netra_{environment}",
                }
            },
            "pool_config": {
                "pool_size": 5,
                "max_overflow": 10, 
                "pool_timeout": 30.0,
                "pool_recycle": 3600,
                "pool_pre_ping": True,
                "pool_reset_on_return": "rollback",
            }
        }


def is_cloud_sql_environment(environment: str) -> bool:
    """Check if environment typically uses Cloud SQL.
    
    Args:
        environment: Environment name
        
    Returns:
        True if environment typically uses Cloud SQL
    """
    return environment.lower() in ["staging", "production"]


def get_progressive_retry_config(environment: str) -> Dict[str, any]:
    """Get progressive retry configuration for database connections.
    
    Different environments need different retry strategies:
    - Local: Fast retries with short delays
    - Cloud SQL: Slower retries with exponential backoff
    
    Args:
        environment: Environment name
        
    Returns:
        Dictionary with retry configuration
    """
    if is_cloud_sql_environment(environment):
        return {
            "max_retries": 5,
            "base_delay": 2.0,      # Start with 2 second delay
            "max_delay": 30.0,      # Cap at 30 seconds
            "exponential_base": 2,  # Double delay each retry
            "jitter": True,         # Add randomization to prevent thundering herd
        }
    else:
        return {
            "max_retries": 3,
            "base_delay": 1.0,      # Start with 1 second delay
            "max_delay": 10.0,      # Cap at 10 seconds  
            "exponential_base": 2,
            "jitter": True,
        }


def get_vpc_connector_capacity_config(environment: str) -> Dict[str, any]:
    """Get VPC connector capacity configuration for Issue #1278.
    
    VPC connectors have throughput limits and scaling delays that affect
    database connection establishment under load conditions.
    
    Args:
        environment: Environment name
        
    Returns:
        Dictionary with VPC connector capacity configuration
    """
    if is_cloud_sql_environment(environment):
        return {
            "throughput_baseline_gbps": 2.0,      # VPC connector baseline throughput
            "throughput_max_gbps": 10.0,          # VPC connector maximum throughput
            "scaling_delay_seconds": 30.0,        # Time for VPC connector auto-scaling
            "concurrent_connection_limit": 50,    # Practical concurrent connection limit
            "capacity_pressure_threshold": 0.7,   # Threshold for capacity pressure monitoring
            "scaling_buffer_timeout": 20.0,       # Additional timeout during scaling events
            "monitoring_enabled": True,           # Enable VPC connector monitoring
            "capacity_aware_timeouts": True,      # Adjust timeouts based on VPC capacity
        }
    else:
        return {
            "throughput_baseline_gbps": None,     # No VPC connector in local/test
            "scaling_delay_seconds": 0.0,
            "concurrent_connection_limit": 1000,  # No practical limit for local
            "capacity_pressure_threshold": 1.0,
            "scaling_buffer_timeout": 0.0,
            "monitoring_enabled": False,
            "capacity_aware_timeouts": False,
        }


def calculate_capacity_aware_timeout(environment: str, base_timeout: float) -> float:
    """Calculate timeout with VPC connector capacity awareness.
    
    Adjusts base timeout based on VPC connector capacity constraints
    to prevent Issue #1278 recurrence.
    
    Args:
        environment: Environment name
        base_timeout: Base timeout value
        
    Returns:
        Adjusted timeout accounting for VPC connector capacity
    """
    vpc_config = get_vpc_connector_capacity_config(environment)
    
    if not vpc_config["capacity_aware_timeouts"]:
        return base_timeout
    
    # Add VPC connector scaling buffer
    scaling_buffer = vpc_config["scaling_buffer_timeout"]
    
    # Add capacity pressure buffer (20% increase under pressure)
    capacity_buffer = base_timeout * 0.2
    
    adjusted_timeout = base_timeout + scaling_buffer + capacity_buffer
    
    logger.debug(f"Timeout adjustment for {environment}: {base_timeout}s -> {adjusted_timeout}s "
                f"(scaling: +{scaling_buffer}s, capacity: +{capacity_buffer}s)")
    
    return adjusted_timeout


def log_timeout_configuration(environment: str) -> None:
    """Log the current timeout configuration for debugging.

    Args:
        environment: Environment name
    """
    timeout_config = get_database_timeout_config(environment)
    cloud_sql_config = get_cloud_sql_optimized_config(environment)
    retry_config = get_progressive_retry_config(environment)
    vpc_config = get_vpc_connector_capacity_config(environment)
    logger.info(f"Database Configuration Summary for {environment}:")
    logger.info(f"  Timeout Configuration: {timeout_config}")
    logger.info(f"  Cloud SQL Optimized: {is_cloud_sql_environment(environment)}")
    logger.info(f"  Pool Configuration: {cloud_sql_config['pool_config']}")
    logger.info(f"  Retry Configuration: {retry_config}")
    logger.info(f"  VPC Connector Configuration: {vpc_config}")


def get_connection_monitor() -> DatabaseConnectionMonitor:
    """Get the global database connection monitor instance.

    Returns:
        DatabaseConnectionMonitor instance for recording and tracking connection metrics
    """
    return _connection_monitor


def monitor_connection_attempt(environment: str, connection_time: float, success: bool) -> None:
    """Helper function to monitor a database connection attempt.

    Args:
        environment: Environment name (development, test, staging, production)
        connection_time: Time taken for connection in seconds
        success: Whether the connection was successful
    """
    timeout_config = get_database_timeout_config(environment)
    _connection_monitor.record_connection_attempt(environment, connection_time, success, timeout_config)


def get_connection_performance_summary(environment: str) -> Dict[str, Any]:
    """Get comprehensive connection performance summary for an environment.

    Args:
        environment: Environment name

    Returns:
        Dictionary containing performance metrics and status
    """
    return _connection_monitor.get_performance_summary(environment)


def register_connection_alert_handler(callback: Callable[[str, Dict[str, Any]], None]) -> None:
    """Register a callback function to handle connection performance alerts.

    Args:
        callback: Function that takes (environment, alert_data) and handles the alert
    """
    _connection_monitor.register_alert_callback(callback)


def check_vpc_connector_performance(environment: str) -> Dict[str, Any]:
    """Check VPC connector performance for Cloud SQL environments.

    This function provides baseline performance metrics for VPC connector
    connections to help identify network-level issues.

    Args:
        environment: Environment name

    Returns:
        Dictionary with VPC connector performance assessment
    """
    if not is_cloud_sql_environment(environment):
        return {
            'environment': environment,
            'vpc_connector_required': False,
            'status': 'not_applicable',
            'message': 'VPC connector monitoring only applies to Cloud SQL environments'
        }

    metrics = _connection_monitor.get_environment_metrics(environment)
    timeout_config = get_database_timeout_config(environment)

    if not metrics or metrics.connection_attempts == 0:
        return {
            'environment': environment,
            'vpc_connector_required': True,
            'status': 'no_data',
            'message': 'No connection attempts recorded yet',
            'baseline_timeout': timeout_config.get('connection_timeout', 25.0)
        }

    # VPC connector baseline expectations for Cloud SQL
    vpc_baseline = {
        'staging': {
            'expected_avg_time': 5.0,    # 5s average for staging
            'warning_threshold': 12.0,   # 80% of 15s timeout
            'critical_threshold': 20.0,  # Close to 25s timeout
        },
        'production': {
            'expected_avg_time': 8.0,    # 8s average for production
            'warning_threshold': 48.0,   # 80% of 60s timeout
            'critical_threshold': 57.0,  # 95% of 60s timeout
        }
    }

    baseline = vpc_baseline.get(environment.lower(), vpc_baseline['staging'])
    avg_time = metrics.get_average_connection_time()
    recent_avg = metrics.get_recent_average_connection_time()

    # Assess VPC connector performance
    status = 'healthy'
    issues = []

    if avg_time > baseline['critical_threshold']:
        status = 'critical'
        issues.append(f"Average connection time {avg_time:.2f}s exceeds critical threshold {baseline['critical_threshold']}s")
    elif avg_time > baseline['warning_threshold']:
        status = 'warning'
        issues.append(f"Average connection time {avg_time:.2f}s exceeds warning threshold {baseline['warning_threshold']}s")

    if recent_avg > avg_time * 1.5:
        status = 'degrading' if status == 'healthy' else status
        issues.append(f"Recent performance degradation: {recent_avg:.2f}s vs {avg_time:.2f}s average")

    if metrics.get_timeout_violation_rate() > 10.0:
        status = 'critical' if status != 'critical' else status
        issues.append(f"High timeout violation rate: {metrics.get_timeout_violation_rate():.1f}%")

    return {
        'environment': environment,
        'vpc_connector_required': True,
        'status': status,
        'connection_attempts': metrics.connection_attempts,
        'average_connection_time': avg_time,
        'recent_average_connection_time': recent_avg,
        'expected_baseline': baseline['expected_avg_time'],
        'warning_threshold': baseline['warning_threshold'],
        'critical_threshold': baseline['critical_threshold'],
        'timeout_violation_rate': metrics.get_timeout_violation_rate(),
        'performance_issues': issues,
        'recommendations': _get_vpc_performance_recommendations(status, issues, environment)
    }


def _get_vpc_performance_recommendations(status: str, issues: list, environment: str) -> list:
    """Get recommendations for VPC connector performance issues."""
    recommendations = []

    if status == 'critical':
        recommendations.extend([
            "Immediately check VPC connector status and configuration",
            "Verify Cloud SQL instance is not under heavy load",
            "Check network connectivity between VPC and Cloud SQL",
            "Consider increasing timeout thresholds if this is persistent"
        ])
    elif status == 'warning':
        recommendations.extend([
            "Monitor VPC connector performance over next hour",
            "Check Cloud SQL instance metrics for resource utilization",
            "Review recent network changes or deployments"
        ])
    elif status == 'degrading':
        recommendations.extend([
            "Investigate recent performance degradation",
            "Check for changes in Cloud SQL instance configuration",
            "Monitor for continued degradation patterns"
        ])

    if any('timeout violation' in issue.lower() for issue in issues):
        recommendations.append(f"Consider reviewing timeout configuration for {environment} environment")

    return recommendations


def log_connection_performance_summary(environment: str) -> None:
    """Log a comprehensive connection performance summary for debugging.

    Args:
        environment: Environment name
    """
    summary = get_connection_performance_summary(environment)
    vpc_performance = check_vpc_connector_performance(environment)

    logger.info(f"Connection Performance Summary for {environment}:")
    logger.info(f"  Status: {summary.get('status', 'unknown')}")
    logger.info(f"  Connection Attempts: {summary.get('connection_attempts', 0)}")
    logger.info(f"  Success Rate: {summary.get('success_rate', 0):.1f}%")
    logger.info(f"  Average Connection Time: {summary.get('average_connection_time', 0):.2f}s")
    logger.info(f"  Recent Average: {summary.get('recent_average_connection_time', 0):.2f}s")
    logger.info(f"  Timeout Violations: {summary.get('timeout_violation_rate', 0):.1f}%")

    if vpc_performance['vpc_connector_required']:
        logger.info(f"  VPC Connector Status: {vpc_performance['status']}")
        if vpc_performance.get('performance_issues'):
            logger.warning(f"  VPC Performance Issues: {'; '.join(vpc_performance['performance_issues'])}")
        if vpc_performance.get('recommendations'):
            logger.info(f"  Recommendations: {'; '.join(vpc_performance['recommendations'])}")
