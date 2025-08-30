"""
Security Monitoring Module for Mock Token Detection and Security Events.

This module provides comprehensive monitoring and alerting for security events,
with special focus on detecting mock token usage across the system.

Business Value: Platform/Internal - Security & Risk Reduction
Prevents mock tokens from being used in production environments and provides
comprehensive security event monitoring and alerting capabilities.
"""

import re
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
import asyncio
import threading
import json

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.tracing import TracingManager
from netra_backend.app.core.isolated_environment import get_env


class SecurityEventSeverity(Enum):
    """Security event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEventType(Enum):
    """Types of security events."""
    MOCK_TOKEN_DETECTED = "mock_token_detected"
    AUTHENTICATION_FAILURE = "authentication_failure"
    AUTHORIZATION_FAILURE = "authorization_failure"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_TOKEN_FORMAT = "invalid_token_format"
    TOKEN_EXPIRY_ANOMALY = "token_expiry_anomaly"


@dataclass
class SecurityEvent:
    """Security event data structure."""
    event_type: SecurityEventType
    severity: SecurityEventSeverity
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None


@dataclass 
class SecurityMetrics:
    """Security metrics tracking structure."""
    total_events: int = 0
    events_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    events_by_severity: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    mock_token_detections: int = 0
    last_event_time: Optional[datetime] = None
    recent_events: deque = field(default_factory=lambda: deque(maxlen=100))


class SecurityMonitoringManager:
    """
    Comprehensive security monitoring and alerting system.
    
    Features:
    - Mock token detection and alerting
    - Security event logging with severity levels
    - Metrics collection for dashboards
    - Integration with existing logging and tracing
    - Production alerting capabilities
    - Rate limiting and anomaly detection
    """

    def __init__(self):
        self.logger = central_logger.get_logger(__name__)
        self.tracing_manager = TracingManager()
        self._metrics = SecurityMetrics()
        self._alerting_enabled = self._is_production_environment()
        self._alert_callbacks: List[Callable] = []
        self._lock = threading.RLock()
        
        # Note: Mock token detection patterns are now handled in detect_mock_token method
        
        # Rate limiting for security events (events per minute)
        self._rate_limits = {
            SecurityEventType.MOCK_TOKEN_DETECTED: 10,
            SecurityEventType.AUTHENTICATION_FAILURE: 50,
            SecurityEventType.AUTHORIZATION_FAILURE: 30,
        }
        self._rate_tracking = defaultdict(lambda: deque(maxlen=100))
        
        self.logger.info("SecurityMonitoringManager initialized", extra={
            "alerting_enabled": self._alerting_enabled,
            "mock_detection": "enhanced_context_aware"
        })

    def detect_mock_token(self, token: str) -> bool:
        """
        Detect if a token appears to be a mock/test token.
        
        This function distinguishes between:
        - Legitimate test tokens (properly formatted for test environments)
        - Actual mock tokens (simple placeholders that shouldn't be used)
        
        Args:
            token: The token string to analyze
            
        Returns:
            bool: True if token appears to be a mock token that should be blocked
        """
        if not token or not isinstance(token, str):
            return False
            
        token_stripped = token.strip()
        token_lower = token_stripped.lower()
        
        # Get current environment
        current_env = get_env().get('ENVIRONMENT', '').lower()
        is_test_env = current_env in ['test', 'testing', 'development', 'dev', 'local']
        
        # Allow JWT-structured tokens even if they contain test keywords
        # JWTs have 3 base64-encoded parts separated by dots
        if token_stripped.count('.') == 2:
            parts = token_stripped.split('.')
            # Basic check for JWT structure (each part should be base64-like)
            if all(len(part) > 10 and part.replace('-', '').replace('_', '').replace('=', '').isalnum() 
                   for part in parts):
                return False  # This looks like a real JWT, even if it has test data
        
        # Allow properly formatted test tokens in test environments
        if is_test_env:
            # Allow tokens that follow secure patterns even with test prefixes
            if re.match(r'^test-jwt-[A-Za-z0-9_-]{32,}$', token_stripped):
                return False  # This is a properly generated test token
            if re.match(r'^[A-Za-z0-9_-]{32,}$', token_stripped):
                return False  # This looks like a proper random token
        
        # Check for obvious mock/placeholder patterns (short, simple tokens)
        obvious_mock_patterns = [
            re.compile(r'^mock_?token_?[a-zA-Z0-9_-]*$'),
            re.compile(r'^test_?token_?[a-zA-Z0-9_-]*$'),
            re.compile(r'^fake_?[a-zA-Z0-9_-]*$'),
            re.compile(r'^dummy_?[a-zA-Z0-9_-]*$'),
            re.compile(r'^placeholder_?[a-zA-Z0-9_-]*$'),
            re.compile(r'^example_?[a-zA-Z0-9_-]*$'),
        ]
        
        for pattern in obvious_mock_patterns:
            if pattern.match(token_lower):
                return True
        
        # Check for tokens that are clearly placeholders (very short or simple)
        if len(token_stripped) < 16:
            simple_mock_indicators = ['mock', 'test', 'fake', 'dummy', 'placeholder', 'example']
            if any(indicator in token_lower for indicator in simple_mock_indicators):
                return True
        
        # Check for hardcoded test values that shouldn't be in production
        if not is_test_env:
            production_forbidden = [
                'mock_token', 'test_token', 'fake_token', 'dummy_token',
                'placeholder', 'example_token', '123456', 'token123',
                'default_token', 'sample_token'
            ]
            if token_lower in production_forbidden:
                return True
        
        return False

    def log_security_event(self, event_type: str, details: Dict[str, Any],
                          severity: str = "medium", context: Optional[str] = None) -> None:
        """
        Log a security event with appropriate severity and context.
        
        Args:
            event_type: Type of security event (string or SecurityEventType)
            details: Event details and context
            severity: Event severity level
            context: Additional context information
        """
        try:
            # Convert string types to enums
            if isinstance(event_type, str):
                try:
                    event_type_enum = SecurityEventType(event_type)
                except ValueError:
                    event_type_enum = SecurityEventType.SUSPICIOUS_ACTIVITY
            else:
                event_type_enum = event_type
                
            if isinstance(severity, str):
                try:
                    severity_enum = SecurityEventSeverity(severity.lower())
                except ValueError:
                    severity_enum = SecurityEventSeverity.MEDIUM
            else:
                severity_enum = severity

            # Create security event
            event = SecurityEvent(
                event_type=event_type_enum,
                severity=severity_enum,
                message=details.get('message', f'Security event: {event_type_enum.value}'),
                context=details,
                source_ip=details.get('source_ip'),
                user_id=details.get('user_id'),
                request_id=details.get('request_id'),
                trace_id=self.tracing_manager.get_current_trace_id()
            )

            # Check rate limits
            if self._is_rate_limited(event_type_enum):
                self.logger.debug(f"Security event rate limited: {event_type_enum.value}")
                return

            # Update metrics
            with self._lock:
                self._update_metrics(event)

            # Log the event
            log_context = {
                "security_event": True,
                "event_type": event_type_enum.value,
                "severity": severity_enum.value,
                "timestamp": event.timestamp.isoformat(),
                "trace_id": event.trace_id,
                **details
            }

            # Use appropriate log level based on severity
            if severity_enum == SecurityEventSeverity.CRITICAL:
                self.logger.critical(event.message, **log_context)
            elif severity_enum == SecurityEventSeverity.HIGH:
                self.logger.error(event.message, **log_context)
            elif severity_enum == SecurityEventSeverity.MEDIUM:
                self.logger.warning(event.message, **log_context)
            else:
                self.logger.info(event.message, **log_context)

            # Trigger alerts for high-severity events
            if self._alerting_enabled and severity_enum in [SecurityEventSeverity.HIGH, SecurityEventSeverity.CRITICAL]:
                self._trigger_alerts(event)

        except Exception as e:
            self.logger.error(f"Failed to log security event: {e}", exc_info=True)

    def increment_security_metric(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a security metric for monitoring dashboards.
        
        Args:
            metric_name: Name of the metric to increment
            tags: Optional tags for metric labeling
        """
        try:
            with self._lock:
                # Update internal metrics
                if hasattr(self._metrics, metric_name):
                    current_value = getattr(self._metrics, metric_name, 0)
                    setattr(self._metrics, metric_name, current_value + 1)
                else:
                    # Handle custom metrics
                    if not hasattr(self._metrics, 'custom_metrics'):
                        self._metrics.custom_metrics = defaultdict(int)
                    self._metrics.custom_metrics[metric_name] += 1

            # Log metric for external monitoring systems
            self.logger.info(f"Security metric incremented: {metric_name}", extra={
                "metric_name": metric_name,
                "metric_type": "security_counter",
                "tags": tags or {},
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        except Exception as e:
            self.logger.error(f"Failed to increment security metric {metric_name}: {e}")

    def check_and_alert_mock_token(self, token: str, context: str) -> bool:
        """
        Check for mock token usage and alert if detected.
        
        Args:
            token: Token to check
            context: Context where token was used (e.g., "websocket_auth", "api_request")
            
        Returns:
            bool: True if mock token detected
        """
        if not token:
            return False

        is_mock = self.detect_mock_token(token)
        
        if is_mock:
            # Determine severity based on environment
            severity = SecurityEventSeverity.CRITICAL if self._is_production_environment() else SecurityEventSeverity.HIGH
            
            # Log the security event
            self.log_security_event(
                event_type=SecurityEventType.MOCK_TOKEN_DETECTED,
                severity=severity,
                details={
                    "message": f"Mock token detected in {context}",
                    "token_prefix": token[:12] + "..." if len(token) > 12 else token,
                    "context": context,
                    "environment": get_env().get('ENVIRONMENT', 'unknown'),
                    "detection_method": "enhanced_context_aware",
                    "detection_time": datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Increment specific metric
            self.increment_security_metric("mock_token_detections", {
                "context": context,
                "environment": get_env().get('ENVIRONMENT', 'unknown')
            })
            
            return True
            
        return False

    def get_security_metrics(self) -> Dict[str, Any]:
        """
        Get current security metrics for monitoring dashboards.
        
        Returns:
            Dict containing current security metrics
        """
        with self._lock:
            metrics = {
                "total_events": self._metrics.total_events,
                "events_by_type": dict(self._metrics.events_by_type),
                "events_by_severity": dict(self._metrics.events_by_severity),
                "mock_token_detections": self._metrics.mock_token_detections,
                "last_event_time": self._metrics.last_event_time.isoformat() if self._metrics.last_event_time else None,
                "recent_events_count": len(self._metrics.recent_events),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "alerting_enabled": self._alerting_enabled,
            }
            
            # Add custom metrics if they exist
            if hasattr(self._metrics, 'custom_metrics'):
                metrics["custom_metrics"] = dict(self._metrics.custom_metrics)
                
            return metrics

    def get_recent_security_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent security events for investigation.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent security events
        """
        with self._lock:
            recent_events = list(self._metrics.recent_events)[-limit:]
            return [
                {
                    "event_type": event.event_type.value,
                    "severity": event.severity.value,
                    "message": event.message,
                    "timestamp": event.timestamp.isoformat(),
                    "context": event.context,
                    "source_ip": event.source_ip,
                    "user_id": event.user_id,
                    "trace_id": event.trace_id
                }
                for event in recent_events
            ]

    def register_alert_callback(self, callback: Callable[[SecurityEvent], None]) -> None:
        """
        Register a callback function for security alerts.
        
        Args:
            callback: Function to call when alerts are triggered
        """
        self._alert_callbacks.append(callback)
        self.logger.info(f"Alert callback registered: {callback.__name__}")

    def _is_production_environment(self) -> bool:
        """Check if running in production environment."""
        env = get_env().get('ENVIRONMENT', '').lower()
        return env in ['production', 'prod', 'staging']

    def _is_rate_limited(self, event_type: SecurityEventType) -> bool:
        """Check if event type is rate limited."""
        if event_type not in self._rate_limits:
            return False
            
        now = time.time()
        cutoff = now - 60  # 1 minute window
        
        # Clean old entries
        while self._rate_tracking[event_type] and self._rate_tracking[event_type][0] < cutoff:
            self._rate_tracking[event_type].popleft()
        
        # Check if over limit
        if len(self._rate_tracking[event_type]) >= self._rate_limits[event_type]:
            return True
            
        # Add current event
        self._rate_tracking[event_type].append(now)
        return False

    def _update_metrics(self, event: SecurityEvent) -> None:
        """Update internal metrics with new event."""
        self._metrics.total_events += 1
        self._metrics.events_by_type[event.event_type.value] += 1
        self._metrics.events_by_severity[event.severity.value] += 1
        self._metrics.last_event_time = event.timestamp
        self._metrics.recent_events.append(event)
        
        if event.event_type == SecurityEventType.MOCK_TOKEN_DETECTED:
            self._metrics.mock_token_detections += 1

    def _trigger_alerts(self, event: SecurityEvent) -> None:
        """Trigger alerts for high-severity events."""
        try:
            # Call registered callbacks
            for callback in self._alert_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    self.logger.error(f"Alert callback failed: {e}")
            
            # Log alert for external monitoring
            self.logger.critical("SECURITY ALERT TRIGGERED", extra={
                "alert": True,
                "event_type": event.event_type.value,
                "severity": event.severity.value,
                "message": event.message,
                "context": event.context,
                "timestamp": event.timestamp.isoformat(),
                "environment": get_env().get('ENVIRONMENT', 'unknown')
            })
            
        except Exception as e:
            self.logger.error(f"Failed to trigger alerts: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on security monitoring system.
        
        Returns:
            Dict containing health status
        """
        try:
            with self._lock:
                health_status = {
                    "status": "healthy",
                    "total_events_processed": self._metrics.total_events,
                    "alerting_enabled": self._alerting_enabled,
                    "alert_callbacks_registered": len(self._alert_callbacks),
                    "mock_detection_method": "enhanced_context_aware",
                    "last_activity": self._metrics.last_event_time.isoformat() if self._metrics.last_event_time else None,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            return health_status
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# Global security monitoring instance
security_monitor = SecurityMonitoringManager()


# Convenience functions for easy integration
def detect_mock_token(token: str) -> bool:
    """Convenience function to detect mock tokens."""
    return security_monitor.detect_mock_token(token)


def log_security_event(event_type: str, details: Dict[str, Any], severity: str = "medium") -> None:
    """Convenience function to log security events."""
    security_monitor.log_security_event(event_type, details, severity)


def increment_security_metric(metric_name: str, tags: Optional[Dict[str, str]] = None) -> None:
    """Convenience function to increment security metrics."""
    security_monitor.increment_security_metric(metric_name, tags)


def check_and_alert_mock_token(token: str, context: str) -> bool:
    """Convenience function to check and alert on mock tokens."""
    return security_monitor.check_and_alert_mock_token(token, context)


def get_security_metrics() -> Dict[str, Any]:
    """Convenience function to get security metrics."""
    return security_monitor.get_security_metrics()