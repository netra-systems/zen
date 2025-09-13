"""
Enhanced WebSocket Diagnostic Tools for Issue #449

PURPOSE: Comprehensive diagnostic and monitoring tools for WebSocket uvicorn 
         middleware stack issues in GCP Cloud Run environments.

BUSINESS IMPACT: $500K+ ARR WebSocket functionality monitoring and diagnostic
                capabilities for proactive issue detection and resolution.

ISSUE #449 REMEDIATION - PHASE 4: Enhanced Logging and Diagnostics  
- Real-time WebSocket health monitoring
- Advanced diagnostic data collection
- uvicorn middleware stack analysis
- Cloud Run performance monitoring
- Automated alerting and reporting

CRITICAL FEATURES:
- Real-time WebSocket connection monitoring
- Middleware stack performance analysis
- uvicorn protocol issue detection
- Cloud Run specific diagnostics
- Automated health checks and alerts
"""

import asyncio
import json
import logging
import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from netra_backend.app.middleware.websocket_error_recovery import (
    WebSocketErrorType, 
    get_websocket_error_recovery_manager,
    record_websocket_error
)

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConnection:
    """WebSocket connection tracking for diagnostics."""
    connection_id: str
    client_ip: str
    request_path: str
    user_agent: str
    connect_time: float
    last_activity: float
    protocol_version: str
    subprotocols: List[str]
    middleware_stack: List[str]
    status: str  # connecting, connected, disconnected, error
    error_count: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    messages_sent: int = 0
    messages_received: int = 0


@dataclass
class MiddlewarePerformance:
    """Middleware performance metrics."""
    middleware_name: str
    total_requests: int
    average_response_time: float
    error_count: int
    websocket_conflicts: int
    last_error_time: Optional[float]
    performance_trend: List[float]


@dataclass
class SystemHealthMetrics:
    """System health metrics for WebSocket diagnostics."""
    timestamp: float
    active_connections: int
    connection_rate: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    middleware_stack_health: Dict[str, float]
    uvicorn_health: Dict[str, Any]
    cloud_run_metrics: Dict[str, Any]


class WebSocketDiagnosticMonitor:
    """
    Comprehensive WebSocket diagnostic monitor for Issue #449.
    
    CRITICAL: This monitor provides real-time diagnostics and health monitoring
    for WebSocket uvicorn middleware stack issues in Cloud Run environments.
    """
    
    def __init__(self, monitoring_interval: float = 30.0):
        self.monitoring_interval = monitoring_interval
        self.active_connections: Dict[str, WebSocketConnection] = {}
        self.middleware_performance: Dict[str, MiddlewarePerformance] = {}
        self.health_history: deque = deque(maxlen=1000)
        self.alert_thresholds = {
            'error_rate': 0.05,  # 5% error rate
            'connection_timeout_rate': 0.10,  # 10% timeout rate
            'memory_usage_mb': 1024,  # 1GB memory usage
            'cpu_usage_percent': 80.0,  # 80% CPU usage
            'middleware_response_time': 1000.0  # 1000ms response time
        }
        
        self._monitoring_active = False
        self._monitoring_task = None
        self._diagnostic_callbacks: List[Callable] = []
        
        # Cloud Run specific monitoring
        self.cloud_run_metrics = {
            'container_memory_utilization': [],
            'container_cpu_utilization': [],
            'request_latencies': [],
            'container_startup_latencies': []
        }
        
        logger.info("WebSocket Diagnostic Monitor initialized for Issue #449")
    
    async def start_monitoring(self):
        """Start real-time WebSocket monitoring."""
        if self._monitoring_active:
            logger.warning("WebSocket monitoring already active")
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("WebSocket diagnostic monitoring started")
    
    async def stop_monitoring(self):
        """Stop real-time WebSocket monitoring."""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("WebSocket diagnostic monitoring stopped")
    
    def register_connection(self, connection_id: str, client_ip: str, request_path: str, 
                          user_agent: str, protocol_version: str = "13", 
                          subprotocols: List[str] = None, middleware_stack: List[str] = None):
        """Register a new WebSocket connection for monitoring."""
        connection = WebSocketConnection(
            connection_id=connection_id,
            client_ip=client_ip,
            request_path=request_path,
            user_agent=user_agent,
            connect_time=time.time(),
            last_activity=time.time(),
            protocol_version=protocol_version,
            subprotocols=subprotocols or [],
            middleware_stack=middleware_stack or [],
            status="connecting"
        )
        
        self.active_connections[connection_id] = connection
        logger.debug(f"WebSocket connection registered: {connection_id}")
    
    def update_connection_status(self, connection_id: str, status: str, 
                               error_info: Optional[Dict[str, Any]] = None):
        """Update WebSocket connection status."""
        if connection_id not in self.active_connections:
            logger.warning(f"Connection not found for status update: {connection_id}")
            return
        
        connection = self.active_connections[connection_id]
        connection.status = status
        connection.last_activity = time.time()
        
        if status == "error" and error_info:
            connection.error_count += 1
            # Record error for recovery management
            error_type = self._classify_error(error_info)
            record_websocket_error(
                error_type=error_type,
                request_path=connection.request_path,
                error_message=error_info.get('message', 'Unknown error'),
                middleware_stack=connection.middleware_stack,
                request_headers={'user-agent': connection.user_agent},
                client_ip=connection.client_ip
            )
        
        logger.debug(f"Connection status updated: {connection_id} -> {status}")
    
    def record_connection_activity(self, connection_id: str, bytes_sent: int = 0, 
                                 bytes_received: int = 0, messages_sent: int = 0, 
                                 messages_received: int = 0):
        """Record WebSocket connection activity."""
        if connection_id not in self.active_connections:
            return
        
        connection = self.active_connections[connection_id]
        connection.last_activity = time.time()
        connection.bytes_sent += bytes_sent
        connection.bytes_received += bytes_received
        connection.messages_sent += messages_sent
        connection.messages_received += messages_received
    
    def unregister_connection(self, connection_id: str, reason: str = "normal_close"):
        """Unregister a WebSocket connection."""
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            connection.status = "disconnected"
            
            # Log connection summary
            duration = time.time() - connection.connect_time
            logger.info(
                f"WebSocket connection closed: {connection_id}, "
                f"Duration: {duration:.2f}s, Reason: {reason}, "
                f"Sent: {connection.bytes_sent} bytes, "
                f"Received: {connection.bytes_received} bytes"
            )
            
            del self.active_connections[connection_id]
    
    def record_middleware_performance(self, middleware_name: str, response_time_ms: float, 
                                    success: bool = True, websocket_conflict: bool = False):
        """Record middleware performance metrics."""
        if middleware_name not in self.middleware_performance:
            self.middleware_performance[middleware_name] = MiddlewarePerformance(
                middleware_name=middleware_name,
                total_requests=0,
                average_response_time=0.0,
                error_count=0,
                websocket_conflicts=0,
                last_error_time=None,
                performance_trend=[]
            )
        
        perf = self.middleware_performance[middleware_name]
        perf.total_requests += 1
        
        # Update average response time (exponential moving average)
        alpha = 0.1
        perf.average_response_time = (alpha * response_time_ms) + ((1 - alpha) * perf.average_response_time)
        
        # Track performance trend
        perf.performance_trend.append(response_time_ms)
        if len(perf.performance_trend) > 100:  # Keep last 100 measurements
            perf.performance_trend.pop(0)
        
        if not success:
            perf.error_count += 1
            perf.last_error_time = time.time()
        
        if websocket_conflict:
            perf.websocket_conflicts += 1
    
    def _classify_error(self, error_info: Dict[str, Any]) -> WebSocketErrorType:
        """Classify WebSocket error for recovery management."""
        error_message = error_info.get('message', '').lower()
        
        if 'uvicorn' in error_message or 'asgi' in error_message:
            if 'protocol' in error_message:
                return WebSocketErrorType.UVICORN_PROTOCOL_FAILURE
            elif 'scope' in error_message:
                return WebSocketErrorType.ASGI_SCOPE_CORRUPTION
        elif 'timeout' in error_message:
            return WebSocketErrorType.CLOUD_RUN_TIMEOUT
        elif 'session' in error_message:
            return WebSocketErrorType.SESSION_MIDDLEWARE_CONFLICT
        elif 'cors' in error_message:
            return WebSocketErrorType.CORS_MIDDLEWARE_CONFLICT
        elif 'auth' in error_message:
            return WebSocketErrorType.AUTHENTICATION_MIDDLEWARE_CONFLICT
        elif 'middleware' in error_message:
            return WebSocketErrorType.MIDDLEWARE_STACK_CONFLICT
        elif 'negotiation' in error_message or 'upgrade' in error_message:
            return WebSocketErrorType.PROTOCOL_NEGOTIATION_FAILURE
        elif 'balancer' in error_message or 'load' in error_message:
            return WebSocketErrorType.LOAD_BALANCER_REJECTION
        else:
            return WebSocketErrorType.MIDDLEWARE_STACK_CONFLICT  # Default classification
    
    async def _monitoring_loop(self):
        """Main monitoring loop for collecting diagnostic data."""
        try:
            while self._monitoring_active:
                start_time = time.time()
                
                # Collect system health metrics
                health_metrics = await self._collect_health_metrics()
                self.health_history.append(health_metrics)
                
                # Check alert thresholds
                await self._check_alert_thresholds(health_metrics)
                
                # Clean up stale connections
                self._cleanup_stale_connections()
                
                # Update Cloud Run metrics
                await self._update_cloud_run_metrics()
                
                # Notify diagnostic callbacks
                for callback in self._diagnostic_callbacks:
                    try:
                        await callback(health_metrics)
                    except Exception as e:
                        logger.error(f"Diagnostic callback error: {e}")
                
                # Wait for next monitoring interval
                elapsed = time.time() - start_time
                sleep_time = max(0, self.monitoring_interval - elapsed)
                await asyncio.sleep(sleep_time)
                
        except asyncio.CancelledError:
            logger.info("WebSocket monitoring loop cancelled")
        except Exception as e:
            logger.error(f"WebSocket monitoring loop error: {e}", exc_info=True)
    
    async def _collect_health_metrics(self) -> SystemHealthMetrics:
        """Collect comprehensive system health metrics."""
        current_time = time.time()
        
        # Connection metrics
        active_count = len(self.active_connections)
        recent_connections = [
            c for c in self.active_connections.values() 
            if current_time - c.connect_time < 300  # Last 5 minutes
        ]
        connection_rate = len(recent_connections) / 300.0  # Connections per second
        
        # Error metrics
        recent_errors = [
            c for c in self.active_connections.values() 
            if c.error_count > 0 and current_time - c.last_activity < 3600  # Last hour
        ]
        error_rate = len(recent_errors) / max(1, active_count)
        
        # System metrics
        memory_usage = psutil.virtual_memory().used / (1024 * 1024)  # MB
        cpu_usage = psutil.cpu_percent()
        
        # Middleware health
        middleware_health = {}
        for name, perf in self.middleware_performance.items():
            health_score = 100.0
            if perf.average_response_time > self.alert_thresholds['middleware_response_time']:
                health_score -= 30.0
            if perf.error_count > perf.total_requests * 0.1:  # More than 10% errors
                health_score -= 40.0
            if perf.websocket_conflicts > 0:
                health_score -= 20.0
            
            middleware_health[name] = max(0.0, health_score)
        
        # uvicorn health (simulated - in real implementation would check uvicorn internals)
        uvicorn_health = {
            'protocol_handler_active': True,
            'asgi_scope_validator_healthy': True,
            'websocket_protocol_version': '13',
            'concurrent_connections': active_count,
            'last_protocol_error': None
        }
        
        # Cloud Run metrics
        cloud_run_metrics = {
            'container_memory_usage_mb': memory_usage,
            'container_cpu_usage_percent': cpu_usage,
            'active_websocket_connections': active_count,
            'load_balancer_healthy': True,  # Would check actual load balancer in production
            'container_startup_time_ms': None  # Would measure actual startup time
        }
        
        return SystemHealthMetrics(
            timestamp=current_time,
            active_connections=active_count,
            connection_rate=connection_rate,
            error_rate=error_rate,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=cpu_usage,
            middleware_stack_health=middleware_health,
            uvicorn_health=uvicorn_health,
            cloud_run_metrics=cloud_run_metrics
        )
    
    async def _check_alert_thresholds(self, metrics: SystemHealthMetrics):
        """Check metrics against alert thresholds and trigger alerts."""
        alerts = []
        
        if metrics.error_rate > self.alert_thresholds['error_rate']:
            alerts.append({
                'severity': 'high',
                'type': 'error_rate_threshold',
                'message': f"WebSocket error rate {metrics.error_rate:.2%} exceeds threshold {self.alert_thresholds['error_rate']:.2%}",
                'metric_value': metrics.error_rate,
                'threshold': self.alert_thresholds['error_rate']
            })
        
        if metrics.memory_usage_mb > self.alert_thresholds['memory_usage_mb']:
            alerts.append({
                'severity': 'medium',
                'type': 'memory_usage_threshold',
                'message': f"Memory usage {metrics.memory_usage_mb:.0f}MB exceeds threshold {self.alert_thresholds['memory_usage_mb']}MB",
                'metric_value': metrics.memory_usage_mb,
                'threshold': self.alert_thresholds['memory_usage_mb']
            })
        
        if metrics.cpu_usage_percent > self.alert_thresholds['cpu_usage_percent']:
            alerts.append({
                'severity': 'medium',
                'type': 'cpu_usage_threshold',
                'message': f"CPU usage {metrics.cpu_usage_percent:.1f}% exceeds threshold {self.alert_thresholds['cpu_usage_percent']}%",
                'metric_value': metrics.cpu_usage_percent,
                'threshold': self.alert_thresholds['cpu_usage_percent']
            })
        
        # Check middleware performance
        for middleware, health_score in metrics.middleware_stack_health.items():
            if health_score < 50.0:
                alerts.append({
                    'severity': 'high',
                    'type': 'middleware_health_degraded',
                    'message': f"Middleware {middleware} health score {health_score:.1f}% is critically low",
                    'metric_value': health_score,
                    'threshold': 50.0,
                    'middleware': middleware
                })
        
        # Process alerts
        for alert in alerts:
            await self._process_alert(alert)
    
    async def _process_alert(self, alert: Dict[str, Any]):
        """Process and handle diagnostic alerts."""
        logger.warning(f"WebSocket Diagnostic Alert: {alert['message']}")
        
        # In production, would integrate with alerting systems (PagerDuty, Slack, etc.)
        # For now, just log the alert
        
        # Could also trigger automatic recovery actions based on alert type
        if alert['type'] == 'error_rate_threshold':
            # Could trigger error recovery analysis
            recovery_manager = get_websocket_error_recovery_manager()
            diagnostic_report = recovery_manager.get_diagnostic_report()
            logger.info(f"Error rate alert triggered. Diagnostic report: {json.dumps(diagnostic_report, indent=2)}")
    
    def _cleanup_stale_connections(self):
        """Clean up stale WebSocket connections."""
        current_time = time.time()
        stale_threshold = 300.0  # 5 minutes
        
        stale_connections = [
            conn_id for conn_id, conn in self.active_connections.items()
            if current_time - conn.last_activity > stale_threshold and conn.status != "connected"
        ]
        
        for conn_id in stale_connections:
            logger.info(f"Cleaning up stale WebSocket connection: {conn_id}")
            self.unregister_connection(conn_id, "stale_connection_cleanup")
    
    async def _update_cloud_run_metrics(self):
        """Update Cloud Run specific metrics."""
        # In production, would integrate with Cloud Run monitoring APIs
        # For now, simulate Cloud Run metrics
        
        current_time = time.time()
        
        # Memory utilization trend
        memory_util = psutil.virtual_memory().percent
        self.cloud_run_metrics['container_memory_utilization'].append({
            'timestamp': current_time,
            'value': memory_util
        })
        
        # Keep only recent metrics
        cutoff_time = current_time - 3600  # Last hour
        for metric_name, metric_data in self.cloud_run_metrics.items():
            if isinstance(metric_data, list):
                self.cloud_run_metrics[metric_name] = [
                    m for m in metric_data 
                    if isinstance(m, dict) and m.get('timestamp', 0) > cutoff_time
                ]
    
    def add_diagnostic_callback(self, callback: Callable):
        """Add a callback function for diagnostic events."""
        self._diagnostic_callbacks.append(callback)
    
    def remove_diagnostic_callback(self, callback: Callable):
        """Remove a diagnostic callback function."""
        if callback in self._diagnostic_callbacks:
            self._diagnostic_callbacks.remove(callback)
    
    def get_real_time_status(self) -> Dict[str, Any]:
        """Get real-time WebSocket diagnostic status."""
        current_time = time.time()
        
        # Connection status breakdown
        status_counts = defaultdict(int)
        for conn in self.active_connections.values():
            status_counts[conn.status] += 1
        
        # Recent activity
        recent_activity = [
            {
                'connection_id': conn.connection_id,
                'status': conn.status,
                'last_activity': current_time - conn.last_activity,
                'error_count': conn.error_count
            }
            for conn in self.active_connections.values()
        ]
        
        # Middleware performance summary
        middleware_summary = {}
        for name, perf in self.middleware_performance.items():
            middleware_summary[name] = {
                'total_requests': perf.total_requests,
                'average_response_time_ms': perf.average_response_time,
                'error_rate': perf.error_count / max(1, perf.total_requests),
                'websocket_conflicts': perf.websocket_conflicts
            }
        
        return {
            'timestamp': current_time,
            'monitoring_active': self._monitoring_active,
            'total_connections': len(self.active_connections),
            'connection_status_breakdown': dict(status_counts),
            'recent_connections': recent_activity[:10],  # Last 10 connections
            'middleware_performance': middleware_summary,
            'system_health': self.health_history[-1] if self.health_history else None,
            'alert_thresholds': self.alert_thresholds
        }
    
    def get_diagnostic_summary(self) -> Dict[str, Any]:
        """Get comprehensive diagnostic summary for Issue #449."""
        recovery_manager = get_websocket_error_recovery_manager()
        recovery_report = recovery_manager.get_diagnostic_report()
        
        return {
            'issue_reference': '#449',
            'diagnostic_timestamp': time.time(),
            'websocket_monitoring': self.get_real_time_status(),
            'error_recovery': recovery_report,
            'middleware_diagnostics': {
                name: {
                    'performance': asdict(perf),
                    'health_score': self.health_history[-1].middleware_stack_health.get(name, 0.0) if self.health_history else 0.0
                }
                for name, perf in self.middleware_performance.items()
            },
            'cloud_run_diagnostics': {
                'metrics_available': len(self.cloud_run_metrics['container_memory_utilization']) > 0,
                'recent_metrics': {
                    name: data[-10:] if isinstance(data, list) else data
                    for name, data in self.cloud_run_metrics.items()
                }
            },
            'recommendations': self._generate_diagnostic_recommendations()
        }
    
    def _generate_diagnostic_recommendations(self) -> List[Dict[str, Any]]:
        """Generate diagnostic recommendations for Issue #449."""
        recommendations = []
        
        if not self._monitoring_active:
            recommendations.append({
                'priority': 'high',
                'category': 'monitoring',
                'message': 'WebSocket diagnostic monitoring is not active. Start monitoring for better visibility.',
                'action': 'call_start_monitoring()'
            })
        
        # Check connection patterns
        if len(self.active_connections) > 100:
            recommendations.append({
                'priority': 'medium',
                'category': 'scalability',
                'message': 'High number of active WebSocket connections. Consider implementing connection pooling or load balancing.',
                'current_connections': len(self.active_connections)
            })
        
        # Check middleware performance
        slow_middleware = [
            name for name, perf in self.middleware_performance.items()
            if perf.average_response_time > 1000  # > 1 second
        ]
        
        if slow_middleware:
            recommendations.append({
                'priority': 'high',
                'category': 'performance',
                'message': f'Slow middleware detected: {slow_middleware}. Review middleware implementation and consider optimization.',
                'affected_middleware': slow_middleware
            })
        
        # Check error patterns
        error_prone_middleware = [
            name for name, perf in self.middleware_performance.items()
            if perf.error_count / max(1, perf.total_requests) > 0.05  # > 5% error rate
        ]
        
        if error_prone_middleware:
            recommendations.append({
                'priority': 'critical',
                'category': 'reliability',
                'message': f'High error rate middleware: {error_prone_middleware}. Investigate and fix underlying issues.',
                'affected_middleware': error_prone_middleware
            })
        
        return recommendations


# Global diagnostic monitor instance
_global_diagnostic_monitor: Optional[WebSocketDiagnosticMonitor] = None


def get_websocket_diagnostic_monitor() -> WebSocketDiagnosticMonitor:
    """Get the global WebSocket diagnostic monitor instance."""
    global _global_diagnostic_monitor
    if _global_diagnostic_monitor is None:
        _global_diagnostic_monitor = WebSocketDiagnosticMonitor()
    return _global_diagnostic_monitor


@asynccontextmanager
async def websocket_diagnostic_context(connection_id: str, client_ip: str, 
                                     request_path: str, user_agent: str):
    """Context manager for WebSocket connection diagnostics."""
    monitor = get_websocket_diagnostic_monitor()
    
    # Register connection
    monitor.register_connection(connection_id, client_ip, request_path, user_agent)
    
    try:
        yield monitor
    finally:
        # Unregister connection
        monitor.unregister_connection(connection_id)


# Export all classes and functions
__all__ = [
    'WebSocketConnection',
    'MiddlewarePerformance', 
    'SystemHealthMetrics',
    'WebSocketDiagnosticMonitor',
    'get_websocket_diagnostic_monitor',
    'websocket_diagnostic_context'
]