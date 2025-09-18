"""
Structured Logging for Authentication Events - Issue #1300 Task #3

Business Value Justification (BVJ):
- Segment: Platform/Internal - Authentication Infrastructure  
- Business Goal: Provide searchable, parseable authentication logs for troubleshooting
- Value Impact: Enable faster resolution of authentication issues and proactive monitoring
- Revenue Impact: Reduce downtime and improve reliability of $500K+ ARR chat functionality

This module implements structured logging for WebSocket authentication events,
providing consistent, searchable, and machine-readable log formats for monitoring
and troubleshooting authentication flows.

Key Features:
1. Structured JSON logging for all authentication events
2. Consistent log schemas with required and optional fields
3. Integration with existing logging infrastructure
4. Support for different log levels and event types
5. Metadata enrichment for debugging and monitoring
6. Export capabilities for log aggregation systems
7. Performance optimized for high-throughput authentication
"""

import json
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
import logging
import threading
from collections import defaultdict

from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.websocket_core.auth_monitoring import AuthEventType

# Base logger for structured auth events
base_logger = get_logger(__name__)


class AuthLogLevel(Enum):
    """Log levels for authentication events."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuthLogCategory(Enum):
    """Categories of authentication logs."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    SESSION_MANAGEMENT = "session_management"
    TOKEN_VALIDATION = "token_validation"
    CONNECTION_MANAGEMENT = "connection_management"
    SECURITY = "security"
    PERFORMANCE = "performance"
    AUDIT = "audit"


@dataclass
class AuthLogSchema:
    """Structured schema for authentication log events."""
    # Required fields
    timestamp: str
    event_type: str
    category: str
    level: str
    message: str
    
    # Authentication context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    connection_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Technical details
    latency_ms: Optional[float] = None
    error_code: Optional[str] = None
    error_details: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Contextual information
    user_agent: Optional[str] = None
    client_ip: Optional[str] = None
    auth_method: Optional[str] = None
    token_type: Optional[str] = None
    
    # System context
    component: str = "WebSocketAuth"
    service: str = "netra_backend"
    environment: Optional[str] = None
    version: str = "1.0.0"
    
    # Issue tracking
    issue: str = "#1300"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AuthStructuredLogger:
    """
    Structured Logger for Authentication Events - Issue #1300 Task #3.
    
    Provides consistent, machine-readable logging for all WebSocket authentication
    events with standardized schemas, metadata enrichment, and integration
    with monitoring systems.
    
    Features:
    - Structured JSON logging with consistent schemas
    - Automatic metadata enrichment
    - Performance metrics tracking
    - Log aggregation and export capabilities
    - Integration with existing logging infrastructure
    - Security-focused redaction of sensitive data
    """
    
    def __init__(self, 
                 service_name: str = "netra_backend",
                 component_name: str = "WebSocketAuth",
                 environment: Optional[str] = None):
        """
        Initialize the structured authentication logger.
        
        Args:
            service_name: Name of the service generating logs
            component_name: Name of the component within the service
            environment: Environment name (development, staging, production)
        """
        self.service_name = service_name
        self.component_name = component_name
        self.environment = environment or self._detect_environment()
        
        # Thread-safe logging
        self._lock = threading.RLock()
        
        # Log statistics
        self._log_counts: Dict[str, int] = defaultdict(int)
        self._start_time = datetime.now(timezone.utc)
        
        # Sensitive data patterns to redact
        self._sensitive_patterns = [
            "password", "secret", "token", "key", "authorization",
            "credential", "session", "cookie"
        ]
        
        # Initialize logger
        self.logger = get_logger(f"{__name__}.{self.component_name}")
        
        # Set up structured logging format
        self._setup_structured_logging()
        
        base_logger.info(f"AuthStructuredLogger initialized for {self.service_name}.{self.component_name} in {self.environment}")
    
    def log_auth_attempt(self,
                        event_type: AuthEventType,
                        user_id: Optional[str] = None,
                        connection_id: Optional[str] = None,
                        success: bool = True,
                        latency_ms: Optional[float] = None,
                        error_code: Optional[str] = None,
                        error_details: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None,
                        **kwargs) -> None:
        """
        Log an authentication attempt with structured format.
        
        Args:
            event_type: Type of authentication event
            user_id: Optional user identifier
            connection_id: Optional connection identifier
            success: Whether the authentication was successful
            latency_ms: Authentication latency in milliseconds
            error_code: Optional error code for failures
            error_details: Optional error details for failures
            metadata: Optional additional metadata
            **kwargs: Additional context fields
        """
        try:
            with self._lock:
                # Determine log level based on success and event type
                level = self._determine_log_level(event_type, success, error_code)
                
                # Create base message
                message = self._create_message(event_type, success, user_id, connection_id)
                
                # Create structured log entry
                log_entry = AuthLogSchema(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    event_type=event_type.value,
                    category=self._categorize_event(event_type).value,
                    level=level.value,
                    message=message,
                    user_id=self._sanitize_user_id(user_id),
                    connection_id=connection_id,
                    latency_ms=latency_ms,
                    error_code=error_code,
                    error_details=self._sanitize_error_details(error_details),
                    metadata=self._sanitize_metadata(metadata or {}),
                    component=self.component_name,
                    service=self.service_name,
                    environment=self.environment,
                    **{k: v for k, v in kwargs.items() if k not in ['component', 'service', 'environment']}
                )
                
                # Log with appropriate level
                self._emit_log(level, log_entry)
                
                # Update statistics
                self._update_log_stats(event_type.value, level.value, success)
                
        except Exception as e:
            # Fallback logging to ensure we don't lose the original event
            base_logger.error(f"Failed to create structured auth log: {e}")
            self._fallback_log(event_type, success, user_id, connection_id, error_details)
    
    def log_security_event(self,
                          event_description: str,
                          severity: str = "warning",
                          user_id: Optional[str] = None,
                          connection_id: Optional[str] = None,
                          security_details: Optional[Dict[str, Any]] = None,
                          **kwargs) -> None:
        """
        Log a security-related authentication event.
        
        Args:
            event_description: Description of the security event
            severity: Severity level (info, warning, error, critical)
            user_id: Optional user identifier
            connection_id: Optional connection identifier
            security_details: Optional security-specific metadata
            **kwargs: Additional context fields
        """
        try:
            level = AuthLogLevel(severity.upper())
            
            log_entry = AuthLogSchema(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="security_event",
                category=AuthLogCategory.SECURITY.value,
                level=level.value,
                message=f"SECURITY: {event_description}",
                user_id=self._sanitize_user_id(user_id),
                connection_id=connection_id,
                metadata=self._sanitize_metadata(security_details or {}),
                component=self.component_name,
                service=self.service_name,
                environment=self.environment,
                **kwargs
            )
            
            self._emit_log(level, log_entry)
            self._update_log_stats("security_event", level.value, True)
            
        except Exception as e:
            base_logger.error(f"Failed to log security event: {e}")
    
    def log_performance_event(self,
                             operation: str,
                             duration_ms: float,
                             user_id: Optional[str] = None,
                             connection_id: Optional[str] = None,
                             performance_details: Optional[Dict[str, Any]] = None,
                             **kwargs) -> None:
        """
        Log a performance-related authentication event.
        
        Args:
            operation: Name of the operation being measured
            duration_ms: Duration of the operation in milliseconds
            user_id: Optional user identifier
            connection_id: Optional connection identifier
            performance_details: Optional performance-specific metadata
            **kwargs: Additional context fields
        """
        try:
            # Determine level based on duration
            level = AuthLogLevel.INFO
            if duration_ms > 2000:  # >2 seconds
                level = AuthLogLevel.WARNING
            elif duration_ms > 5000:  # >5 seconds
                level = AuthLogLevel.ERROR
            
            log_entry = AuthLogSchema(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="performance_event",
                category=AuthLogCategory.PERFORMANCE.value,
                level=level.value,
                message=f"PERFORMANCE: {operation} completed in {duration_ms:.1f}ms",
                user_id=self._sanitize_user_id(user_id),
                connection_id=connection_id,
                latency_ms=duration_ms,
                metadata=self._sanitize_metadata(performance_details or {}),
                component=self.component_name,
                service=self.service_name,
                environment=self.environment,
                **kwargs
            )
            
            self._emit_log(level, log_entry)
            self._update_log_stats("performance_event", level.value, True)
            
        except Exception as e:
            base_logger.error(f"Failed to log performance event: {e}")
    
    def log_audit_event(self,
                       action: str,
                       user_id: Optional[str] = None,
                       connection_id: Optional[str] = None,
                       result: str = "success",
                       audit_details: Optional[Dict[str, Any]] = None,
                       **kwargs) -> None:
        """
        Log an audit trail event for authentication actions.
        
        Args:
            action: The action being audited
            user_id: Optional user identifier
            connection_id: Optional connection identifier
            result: Result of the action (success, failure, etc.)
            audit_details: Optional audit-specific metadata
            **kwargs: Additional context fields
        """
        try:
            level = AuthLogLevel.INFO if result == "success" else AuthLogLevel.WARNING
            
            log_entry = AuthLogSchema(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="audit_event",
                category=AuthLogCategory.AUDIT.value,
                level=level.value,
                message=f"AUDIT: {action} - {result}",
                user_id=self._sanitize_user_id(user_id),
                connection_id=connection_id,
                metadata=self._sanitize_metadata(audit_details or {}),
                component=self.component_name,
                service=self.service_name,
                environment=self.environment,
                **kwargs
            )
            
            self._emit_log(level, log_entry)
            self._update_log_stats("audit_event", level.value, result == "success")
            
        except Exception as e:
            base_logger.error(f"Failed to log audit event: {e}")
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get logging statistics."""
        with self._lock:
            uptime_seconds = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            
            total_logs = sum(self._log_counts.values())
            logs_per_second = total_logs / uptime_seconds if uptime_seconds > 0 else 0
            
            return {
                "total_logs": total_logs,
                "logs_per_second": round(logs_per_second, 2),
                "uptime_seconds": round(uptime_seconds, 2),
                "log_counts_by_type": dict(self._log_counts),
                "start_time": self._start_time.isoformat(),
                "current_time": datetime.now(timezone.utc).isoformat(),
                "service": self.service_name,
                "component": self.component_name,
                "environment": self.environment
            }
    
    def export_log_config(self) -> Dict[str, Any]:
        """Export logger configuration for monitoring systems."""
        return {
            "logger_info": {
                "service": self.service_name,
                "component": self.component_name,
                "environment": self.environment,
                "version": "1.0.0",
                "issue": "#1300"
            },
            "schema_version": "1.0",
            "supported_event_types": [event.value for event in AuthEventType],
            "supported_categories": [category.value for category in AuthLogCategory],
            "supported_levels": [level.value for level in AuthLogLevel],
            "sensitive_data_redaction": True,
            "structured_format": "json",
            "statistics": self.get_log_statistics()
        }
    
    def _setup_structured_logging(self) -> None:
        """Set up structured logging configuration."""
        try:
            # Configure JSON formatter if needed
            # This is a placeholder - actual implementation would depend on logging infrastructure
            pass
        except Exception as e:
            base_logger.warning(f"Failed to set up structured logging: {e}")
    
    def _determine_log_level(self, 
                           event_type: AuthEventType, 
                           success: bool, 
                           error_code: Optional[str]) -> AuthLogLevel:
        """Determine appropriate log level for an event."""
        if not success:
            # Failed authentication events
            if event_type in [AuthEventType.AUTH_FAILURE, AuthEventType.PERMISSION_DENIED]:
                if error_code in ["INVALID_TOKEN", "TOKEN_EXPIRED"]:
                    return AuthLogLevel.WARNING
                else:
                    return AuthLogLevel.ERROR
            elif event_type == AuthEventType.CONNECTION_DROPPED:
                return AuthLogLevel.WARNING
            else:
                return AuthLogLevel.ERROR
        else:
            # Successful events
            if event_type in [AuthEventType.LOGIN, AuthEventType.REGISTER]:
                return AuthLogLevel.INFO
            elif event_type == AuthEventType.LOGOUT:
                return AuthLogLevel.INFO
            elif event_type in [AuthEventType.TOKEN_VALIDATION, AuthEventType.JWT_DECODE]:
                return AuthLogLevel.DEBUG
            else:
                return AuthLogLevel.INFO
    
    def _categorize_event(self, event_type: AuthEventType) -> AuthLogCategory:
        """Categorize an authentication event."""
        auth_events = [AuthEventType.LOGIN, AuthEventType.REGISTER, AuthEventType.AUTH_FAILURE]
        session_events = [AuthEventType.SESSION_CREATE, AuthEventType.SESSION_INVALIDATE, AuthEventType.SESSION_TIMEOUT]
        token_events = [AuthEventType.TOKEN_VALIDATION, AuthEventType.JWT_DECODE, AuthEventType.TOKEN_EXPIRED, AuthEventType.INVALID_TOKEN]
        connection_events = [AuthEventType.CONNECTION_UPGRADE, AuthEventType.WEBSOCKET_HANDSHAKE, AuthEventType.CONNECTION_CLOSE, AuthEventType.CONNECTION_DROPPED]
        security_events = [AuthEventType.PERMISSION_DENIED]
        
        if event_type in auth_events:
            return AuthLogCategory.AUTHENTICATION
        elif event_type in session_events:
            return AuthLogCategory.SESSION_MANAGEMENT
        elif event_type in token_events:
            return AuthLogCategory.TOKEN_VALIDATION
        elif event_type in connection_events:
            return AuthLogCategory.CONNECTION_MANAGEMENT
        elif event_type in security_events:
            return AuthLogCategory.SECURITY
        else:
            return AuthLogCategory.AUTHENTICATION
    
    def _create_message(self, 
                       event_type: AuthEventType, 
                       success: bool, 
                       user_id: Optional[str], 
                       connection_id: Optional[str]) -> str:
        """Create a human-readable message for the log entry."""
        user_info = f"user {user_id[:8]}..." if user_id else "unknown user"
        conn_info = f"connection {connection_id}" if connection_id else "unknown connection"
        
        if success:
            return f"{event_type.value.replace('_', ' ').title()} successful for {user_info} on {conn_info}"
        else:
            return f"{event_type.value.replace('_', ' ').title()} failed for {user_info} on {conn_info}"
    
    def _sanitize_user_id(self, user_id: Optional[str]) -> Optional[str]:
        """Sanitize user ID for logging (redact sensitive parts)."""
        if not user_id:
            return None
        
        # If user ID looks like an email, redact the domain
        if "@" in user_id:
            local, domain = user_id.split("@", 1)
            return f"{local[:3]}***@{domain}"
        
        # For other user IDs, show first few characters
        if len(user_id) > 8:
            return f"{user_id[:8]}..."
        
        return user_id
    
    def _sanitize_error_details(self, error_details: Optional[str]) -> Optional[str]:
        """Sanitize error details to remove sensitive information."""
        if not error_details:
            return None
        
        # Remove any potential sensitive data from error messages
        sanitized = error_details
        for pattern in self._sensitive_patterns:
            if pattern in sanitized.lower():
                # Replace the sensitive value with [REDACTED]
                import re
                sanitized = re.sub(
                    rf'{pattern}["\']?\s*[:=]\s*["\']?[^\s"\',}}\]]+',
                    f'{pattern}=[REDACTED]',
                    sanitized,
                    flags=re.IGNORECASE
                )
        
        return sanitized
    
    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize metadata to remove sensitive information."""
        sanitized = {}
        
        for key, value in metadata.items():
            key_lower = key.lower()
            
            # Check if key contains sensitive patterns
            if any(pattern in key_lower for pattern in self._sensitive_patterns):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and any(pattern in value.lower() for pattern in self._sensitive_patterns):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _emit_log(self, level: AuthLogLevel, log_entry: AuthLogSchema) -> None:
        """Emit the structured log entry."""
        try:
            # Convert to JSON string for structured logging
            log_json = log_entry.to_json()
            
            # Emit with appropriate level
            if level == AuthLogLevel.DEBUG:
                self.logger.debug(log_entry.message, extra={"structured_data": log_entry.to_dict()})
            elif level == AuthLogLevel.INFO:
                self.logger.info(log_entry.message, extra={"structured_data": log_entry.to_dict()})
            elif level == AuthLogLevel.WARNING:
                self.logger.warning(log_entry.message, extra={"structured_data": log_entry.to_dict()})
            elif level == AuthLogLevel.ERROR:
                self.logger.error(log_entry.message, extra={"structured_data": log_entry.to_dict()})
            elif level == AuthLogLevel.CRITICAL:
                self.logger.critical(log_entry.message, extra={"structured_data": log_entry.to_dict()})
            
        except Exception as e:
            base_logger.error(f"Failed to emit structured log: {e}")
            # Fallback to basic logging
            self.logger.info(f"AUTH EVENT: {log_entry.event_type} - {log_entry.message}")
    
    def _update_log_stats(self, event_type: str, level: str, success: bool) -> None:
        """Update logging statistics."""
        try:
            self._log_counts[f"total"] += 1
            self._log_counts[f"event_{event_type}"] += 1
            self._log_counts[f"level_{level}"] += 1
            self._log_counts[f"success_{success}"] += 1
        except Exception as e:
            base_logger.warning(f"Failed to update log stats: {e}")
    
    def _fallback_log(self, 
                     event_type: AuthEventType, 
                     success: bool, 
                     user_id: Optional[str], 
                     connection_id: Optional[str], 
                     error_details: Optional[str]) -> None:
        """Fallback logging when structured logging fails."""
        try:
            message = f"AUTH {event_type.value}: {'SUCCESS' if success else 'FAILURE'}"
            if user_id:
                message += f" user={self._sanitize_user_id(user_id)}"
            if connection_id:
                message += f" conn={connection_id}"
            if error_details:
                message += f" error={self._sanitize_error_details(error_details)}"
            
            if success:
                self.logger.info(message)
            else:
                self.logger.error(message)
                
        except Exception as e:
            base_logger.error(f"Even fallback logging failed: {e}")
    
    def _detect_environment(self) -> str:
        """Detect the current environment."""
        try:
            from shared.isolated_environment import get_env
            env = get_env()
            return env.get("ENVIRONMENT", "unknown")
        except Exception:
            return "unknown"


# Global instance for structured authentication logging
_auth_structured_logger: Optional[AuthStructuredLogger] = None
_logger_lock = threading.Lock()


def get_auth_structured_logger() -> AuthStructuredLogger:
    """Get or create the global structured authentication logger."""
    global _auth_structured_logger
    
    if _auth_structured_logger is None:
        with _logger_lock:
            if _auth_structured_logger is None:
                _auth_structured_logger = AuthStructuredLogger()
                base_logger.info("Created global AuthStructuredLogger for Issue #1300")
    
    return _auth_structured_logger


# Convenience functions for structured authentication logging

def log_auth_event(event_type: AuthEventType, 
                  success: bool = True, 
                  user_id: Optional[str] = None,
                  connection_id: Optional[str] = None,
                  latency_ms: Optional[float] = None,
                  error_code: Optional[str] = None,
                  error_details: Optional[str] = None,
                  **kwargs) -> None:
    """Log an authentication event with structured format."""
    logger = get_auth_structured_logger()
    logger.log_auth_attempt(
        event_type=event_type,
        user_id=user_id,
        connection_id=connection_id,
        success=success,
        latency_ms=latency_ms,
        error_code=error_code,
        error_details=error_details,
        **kwargs
    )


def log_security_event(event_description: str,
                      severity: str = "warning",
                      user_id: Optional[str] = None,
                      connection_id: Optional[str] = None,
                      **kwargs) -> None:
    """Log a security-related authentication event."""
    logger = get_auth_structured_logger()
    logger.log_security_event(
        event_description=event_description,
        severity=severity,
        user_id=user_id,
        connection_id=connection_id,
        **kwargs
    )


def log_performance_event(operation: str,
                         duration_ms: float,
                         user_id: Optional[str] = None,
                         connection_id: Optional[str] = None,
                         **kwargs) -> None:
    """Log a performance-related authentication event."""
    logger = get_auth_structured_logger()
    logger.log_performance_event(
        operation=operation,
        duration_ms=duration_ms,
        user_id=user_id,
        connection_id=connection_id,
        **kwargs
    )


def log_audit_event(action: str,
                   result: str = "success",
                   user_id: Optional[str] = None,
                   connection_id: Optional[str] = None,
                   **kwargs) -> None:
    """Log an audit trail event."""
    logger = get_auth_structured_logger()
    logger.log_audit_event(
        action=action,
        user_id=user_id,
        connection_id=connection_id,
        result=result,
        **kwargs
    )


def get_logging_statistics() -> Dict[str, Any]:
    """Get structured logging statistics."""
    logger = get_auth_structured_logger()
    return logger.get_log_statistics()


def export_logging_config() -> Dict[str, Any]:
    """Export logging configuration for monitoring systems."""
    logger = get_auth_structured_logger()
    return logger.export_log_config()


# Export public interface
__all__ = [
    "AuthStructuredLogger",
    "AuthLogLevel",
    "AuthLogCategory", 
    "AuthLogSchema",
    "get_auth_structured_logger",
    "log_auth_event",
    "log_security_event",
    "log_performance_event",
    "log_audit_event",
    "get_logging_statistics",
    "export_logging_config"
]