from netra_backend.app.logging_config import central_logger
"""
SLO Monitoring Decorators and Integration Helpers

Provides easy-to-use decorators for integrating SLO monitoring into existing code.
"""

import time
import asyncio
import functools
from typing import Callable, Any, Optional, Dict
from contextlib import asynccontextmanager

from netra_backend.app.services.slo_monitoring import get_slo_monitor
from netra_backend.app.core.unified_logging import central_logger

logger = central_logger.get_logger(__name__)


def monitor_chat_response_time(func: Callable) -> Callable:
    """Decorator to monitor chat API response times."""
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            response_time = time.time() - start_time
            
            # Record successful response time
            monitor = get_slo_monitor()
            monitor.record_metric("chat_response_time", response_time, success=True)
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            
            # Record failed response (still track time)
            monitor = get_slo_monitor()
            monitor.record_metric("chat_response_time", response_time, success=False)
            
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            response_time = time.time() - start_time
            
            monitor = get_slo_monitor()
            monitor.record_metric("chat_response_time", response_time, success=True)
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            
            monitor = get_slo_monitor()
            monitor.record_metric("chat_response_time", response_time, success=False)
            
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def monitor_database_query_time(func: Callable) -> Callable:
    """Decorator to monitor database query performance."""
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            query_time = time.time() - start_time
            
            monitor = get_slo_monitor()
            monitor.record_metric("database_query_time", query_time, success=True)
            
            return result
            
        except Exception as e:
            query_time = time.time() - start_time
            
            monitor = get_slo_monitor()
            monitor.record_metric("database_query_time", query_time, success=False)
            
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            query_time = time.time() - start_time
            
            monitor = get_slo_monitor()
            monitor.record_metric("database_query_time", query_time, success=True)
            
            return result
            
        except Exception as e:
            query_time = time.time() - start_time
            
            monitor = get_slo_monitor()
            monitor.record_metric("database_query_time", query_time, success=False)
            
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def monitor_agent_execution_time(func: Callable) -> Callable:
    """Decorator to monitor agent execution times."""
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            monitor = get_slo_monitor()
            monitor.record_metric("agent_execution_time", execution_time, success=True)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            monitor = get_slo_monitor()
            monitor.record_metric("agent_execution_time", execution_time, success=False)
            
            raise
    
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            monitor = get_slo_monitor()
            monitor.record_metric("agent_execution_time", execution_time, success=True)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            monitor = get_slo_monitor()
            monitor.record_metric("agent_execution_time", execution_time, success=False)
            
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def monitor_custom_slo(slo_name: str, success_threshold: Optional[float] = None):
    """Generic decorator for monitoring custom SLO metrics."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Determine success based on threshold if provided
                success = True
                if success_threshold is not None:
                    success = execution_time <= success_threshold
                
                monitor = get_slo_monitor()
                monitor.record_metric(slo_name, execution_time, success=success)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                monitor = get_slo_monitor()
                monitor.record_metric(slo_name, execution_time, success=False)
                
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                success = True
                if success_threshold is not None:
                    success = execution_time <= success_threshold
                
                monitor = get_slo_monitor()
                monitor.record_metric(slo_name, execution_time, success=success)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                monitor = get_slo_monitor()
                monitor.record_metric(slo_name, execution_time, success=False)
                
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


@asynccontextmanager
async def slo_timer(slo_name: str, labels: Optional[Dict[str, str]] = None):
    """Context manager for timing operations and recording SLO metrics."""
    start_time = time.time()
    success = True
    
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        duration = time.time() - start_time
        monitor = get_slo_monitor()
        monitor.record_metric(slo_name, duration, labels=labels, success=success)


class SLORecorder:
    """Helper class for recording SLO metrics with context."""
    
    def __init__(self, slo_name: str, labels: Optional[Dict[str, str]] = None):
        self.slo_name = slo_name
        self.labels = labels or {}
        self.monitor = get_slo_monitor()
    
    def record_success(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Record successful metric."""
        combined_labels = {**self.labels, **(labels or {})}
        self.monitor.record_metric(self.slo_name, value, labels=combined_labels, success=True)
    
    def record_failure(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Record failed metric."""
        combined_labels = {**self.labels, **(labels or {})}
        self.monitor.record_metric(self.slo_name, value, labels=combined_labels, success=False)
    
    def record(self, value: float, success: bool, labels: Optional[Dict[str, str]] = None):
        """Record metric with explicit success/failure."""
        combined_labels = {**self.labels, **(labels or {})}
        self.monitor.record_metric(self.slo_name, value, labels=combined_labels, success=success)


# Convenience instances for common use cases
chat_slo_recorder = SLORecorder("chat_response_time", {"component": "chat"})
database_slo_recorder = SLORecorder("database_query_time", {"component": "database"})
agent_slo_recorder = SLORecorder("agent_execution_time", {"component": "agents"})
websocket_slo_recorder = SLORecorder("websocket_uptime", {"component": "websocket"})


def setup_slo_alert_callbacks():
    """Setup default alert callbacks for SLO violations."""
    monitor = get_slo_monitor()
    
    async def log_alert_callback(alert):
        """Log alert to structured logs."""
        logger.error(f"SLO VIOLATION: {alert.message}", extra={
            "alert_id": alert.alert_id,
            "slo_name": alert.slo_name,
            "severity": alert.severity,
            "current_value": alert.current_value,
            "target_value": alert.target_value,
            "labels": alert.labels
        })
    
    def resolve_alert_callback(alert):
        """Log alert resolution."""
        duration = alert.resolved_at - alert.triggered_at
        logger.info(f"SLO ALERT RESOLVED: {alert.slo_name} after {duration:.1f}s", extra={
            "alert_id": alert.alert_id,
            "slo_name": alert.slo_name,
            "duration_seconds": duration
        })
    
    monitor.add_alert_callback(log_alert_callback)
    monitor.add_alert_callback(resolve_alert_callback)
    
    logger.info("SLO alert callbacks configured")