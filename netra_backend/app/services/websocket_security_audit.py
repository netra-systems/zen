"""WebSocket Security Audit and Validation

Business Value Justification:
- Segment: Platform/Internal (Security Critical)
- Business Goal: Risk Reduction & Compliance
- Value Impact: Prevents data breaches and ensures regulatory compliance
- Strategic Impact: Foundation for secure multi-user AI platform

This module provides comprehensive security validation and audit logging for WebSocket
operations to prevent user data leakage and ensure compliance with security standards.

Key Security Features:
- User context validation and isolation verification
- Event routing security validation
- Comprehensive audit trail for compliance
- Real-time security violation detection
- Automated threat response capabilities

CRITICAL: All WebSocket event operations should be validated through this module
to ensure user data remains properly isolated.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading
from pathlib import Path

from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = central_logger.get_logger(__name__)


class SecurityViolationType(Enum):
    """Types of security violations that can occur."""
    USER_ID_MISMATCH = "user_id_mismatch"
    THREAD_ID_MISMATCH = "thread_id_mismatch"
    RUN_ID_MISMATCH = "run_id_mismatch"
    CONNECTION_USER_MISMATCH = "connection_user_mismatch"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    CONTEXT_ISOLATION_VIOLATION = "context_isolation_violation"
    INVALID_USER_CONTEXT = "invalid_user_context"
    WEBSOCKET_HIJACKING = "websocket_hijacking"
    EVENT_INJECTION = "event_injection"
    PRIVILEGE_ESCALATION = "privilege_escalation"


class SecurityThreatLevel(Enum):
    """Threat levels for security violations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityViolation:
    """Data structure for security violations."""
    violation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    violation_type: SecurityViolationType = SecurityViolationType.UNAUTHORIZED_ACCESS
    threat_level: SecurityThreatLevel = SecurityThreatLevel.MEDIUM
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_context: Optional[Dict[str, Any]] = None
    violation_details: Dict[str, Any] = field(default_factory=dict)
    source_component: Optional[str] = None
    affected_user_id: Optional[str] = None
    requesting_user_id: Optional[str] = None
    remediation_actions: List[str] = field(default_factory=list)


@dataclass
class AuditEvent:
    """Data structure for audit events."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "websocket_operation"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    operation: str = "unknown"
    result: str = "unknown"  # success, failure, blocked
    security_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WebSocketSecurityValidator:
    """Validates WebSocket operations for security compliance.
    
    This class provides comprehensive security validation for WebSocket operations
    to prevent user data leakage and ensure proper user isolation.
    """
    
    def __init__(self):
        """Initialize security validator."""
        self._violation_handlers: List[callable] = []
        self._security_metrics = {
            'violations_detected': 0,
            'validations_performed': 0,
            'blocked_operations': 0,
            'last_validation': None
        }
        
        logger.info("[U+1F6E1][U+FE0F] WebSocket Security Validator initialized")
    
    def validate_user_context_isolation(
        self, 
        user_context: UserExecutionContext,
        operation: str = "unknown"
    ) -> Tuple[bool, Optional[SecurityViolation]]:
        """Validate that user context has proper isolation.
        
        Args:
            user_context: User context to validate
            operation: Operation being performed for logging
            
        Returns:
            Tuple of (is_valid, violation_info)
        """
        self._security_metrics['validations_performed'] += 1
        self._security_metrics['last_validation'] = datetime.now(timezone.utc)
        
        try:
            # Validate context is properly formed
            if not isinstance(user_context, UserExecutionContext):
                violation = SecurityViolation(
                    violation_type=SecurityViolationType.INVALID_USER_CONTEXT,
                    threat_level=SecurityThreatLevel.HIGH,
                    violation_details={
                        "error": "Invalid user context type",
                        "actual_type": type(user_context).__name__,
                        "operation": operation
                    },
                    source_component="WebSocketSecurityValidator"
                )
                return False, violation
            
            # Validate required fields are present
            required_fields = ['user_id', 'thread_id', 'run_id', 'request_id']
            for field in required_fields:
                if not hasattr(user_context, field) or not getattr(user_context, field):
                    violation = SecurityViolation(
                        violation_type=SecurityViolationType.INVALID_USER_CONTEXT,
                        threat_level=SecurityThreatLevel.HIGH,
                        violation_details={
                            "error": f"Missing required field: {field}",
                            "operation": operation,
                            "context_data": user_context.to_dict()
                        },
                        source_component="WebSocketSecurityValidator"
                    )
                    return False, violation
            
            # Check for isolation integrity
            try:
                user_context.verify_isolation()
            except Exception as e:
                violation = SecurityViolation(
                    violation_type=SecurityViolationType.CONTEXT_ISOLATION_VIOLATION,
                    threat_level=SecurityThreatLevel.CRITICAL,
                    violation_details={
                        "error": f"Context isolation violation: {e}",
                        "operation": operation,
                        "user_id": user_context.user_id
                    },
                    source_component="WebSocketSecurityValidator",
                    affected_user_id=user_context.user_id
                )
                return False, violation
            
            logger.debug(f" PASS:  User context validation passed for {user_context.get_correlation_id()}")
            return True, None
            
        except Exception as e:
            violation = SecurityViolation(
                violation_type=SecurityViolationType.INVALID_USER_CONTEXT,
                threat_level=SecurityThreatLevel.HIGH,
                violation_details={
                    "error": f"Context validation exception: {e}",
                    "operation": operation
                },
                source_component="WebSocketSecurityValidator"
            )
            return False, violation
    
    def validate_event_routing(
        self,
        event_user_id: str,
        context_user_id: str,
        event_type: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[SecurityViolation]]:
        """Validate event routing security.
        
        Args:
            event_user_id: User ID from the event
            context_user_id: User ID from the execution context
            event_type: Type of event being routed
            additional_context: Additional context for logging
            
        Returns:
            Tuple of (is_valid, violation_info)
        """
        self._security_metrics['validations_performed'] += 1
        
        # Critical security check: user IDs must match
        if event_user_id != context_user_id:
            violation = SecurityViolation(
                violation_type=SecurityViolationType.USER_ID_MISMATCH,
                threat_level=SecurityThreatLevel.CRITICAL,
                violation_details={
                    "event_user_id": event_user_id,
                    "context_user_id": context_user_id,
                    "event_type": event_type,
                    "additional_context": additional_context or {}
                },
                source_component="WebSocketSecurityValidator",
                affected_user_id=context_user_id,
                requesting_user_id=event_user_id,
                remediation_actions=["Block event routing", "Log security violation", "Alert security team"]
            )
            
            self._security_metrics['violations_detected'] += 1
            logger.error(f" ALERT:  CRITICAL SECURITY VIOLATION: Event routing user ID mismatch - "
                        f"event_user={event_user_id}, context_user={context_user_id}, event={event_type}")
            
            return False, violation
        
        logger.debug(f" PASS:  Event routing validation passed for user {context_user_id}, event {event_type}")
        return True, None
    
    def validate_connection_ownership(
        self,
        connection_user_id: str,
        requesting_user_id: str,
        operation: str,
        connection_id: Optional[str] = None
    ) -> Tuple[bool, Optional[SecurityViolation]]:
        """Validate WebSocket connection ownership.
        
        Args:
            connection_user_id: User ID that owns the connection
            requesting_user_id: User ID requesting access
            operation: Operation being performed
            connection_id: Optional connection ID for logging
            
        Returns:
            Tuple of (is_valid, violation_info)
        """
        self._security_metrics['validations_performed'] += 1
        
        # Critical security check: only connection owner can access
        if connection_user_id != requesting_user_id:
            violation = SecurityViolation(
                violation_type=SecurityViolationType.CONNECTION_USER_MISMATCH,
                threat_level=SecurityThreatLevel.CRITICAL,
                violation_details={
                    "connection_user_id": connection_user_id,
                    "requesting_user_id": requesting_user_id,
                    "operation": operation,
                    "connection_id": connection_id
                },
                source_component="WebSocketSecurityValidator",
                affected_user_id=connection_user_id,
                requesting_user_id=requesting_user_id,
                remediation_actions=["Block connection access", "Log security violation", "Terminate connection"]
            )
            
            self._security_metrics['violations_detected'] += 1
            logger.error(f" ALERT:  CRITICAL SECURITY VIOLATION: Connection access denied - "
                        f"owner={connection_user_id}, requester={requesting_user_id}, op={operation}")
            
            return False, violation
        
        logger.debug(f" PASS:  Connection ownership validation passed for user {requesting_user_id}")
        return True, None
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics for monitoring."""
        return {
            **self._security_metrics,
            'violation_rate': (
                self._security_metrics['violations_detected'] / 
                max(1, self._security_metrics['validations_performed'])
            ),
            'last_validation_ago': (
                (datetime.now(timezone.utc) - self._security_metrics['last_validation']).total_seconds()
                if self._security_metrics['last_validation'] else None
            )
        }


class WebSocketAuditLogger:
    """Comprehensive audit logging for WebSocket operations.
    
    This class provides detailed audit logging for compliance and security monitoring.
    """
    
    def __init__(self, audit_file_path: Optional[str] = None):
        """Initialize audit logger.
        
        Args:
            audit_file_path: Optional path to audit log file
        """
        self._audit_events: List[AuditEvent] = []
        self._max_in_memory_events = 1000
        self._audit_file_path = audit_file_path
        self._lock = threading.Lock()
        
        # Statistics
        self._audit_stats = {
            'events_logged': 0,
            'security_violations': 0,
            'blocked_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'start_time': datetime.now(timezone.utc)
        }
        
        logger.info(f"[U+1F4CB] WebSocket Audit Logger initialized - file: {audit_file_path}")
    
    def log_websocket_operation(
        self,
        operation: str,
        user_id: str,
        result: str = "success",
        session_id: Optional[str] = None,
        security_context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log a WebSocket operation for audit purposes.
        
        Args:
            operation: Operation performed
            user_id: User performing operation
            result: Result of operation (success, failure, blocked)
            session_id: Optional session identifier
            security_context: Security context information
            metadata: Additional metadata
            
        Returns:
            Event ID for correlation
        """
        audit_event = AuditEvent(
            operation=operation,
            user_id=user_id,
            result=result,
            session_id=session_id,
            security_context=security_context or {},
            metadata=metadata or {}
        )
        
        with self._lock:
            self._audit_events.append(audit_event)
            self._audit_stats['events_logged'] += 1
            
            # Update result statistics
            if result == "success":
                self._audit_stats['successful_operations'] += 1
            elif result == "failure":
                self._audit_stats['failed_operations'] += 1
            elif result == "blocked":
                self._audit_stats['blocked_operations'] += 1
            
            # Trim events if too many in memory
            if len(self._audit_events) > self._max_in_memory_events:
                self._audit_events = self._audit_events[-self._max_in_memory_events//2:]
            
            # Write to file if configured
            if self._audit_file_path:
                self._write_audit_event_to_file(audit_event)
        
        logger.info(f"[U+1F4CB] AUDIT: {operation} by user {user_id} - {result} (event_id: {audit_event.event_id})")
        return audit_event.event_id
    
    def log_security_violation(self, violation: SecurityViolation) -> str:
        """Log a security violation.
        
        Args:
            violation: Security violation details
            
        Returns:
            Event ID for correlation
        """
        # Create audit event for the violation
        audit_event = AuditEvent(
            event_type="security_violation",
            operation=f"security_violation_{violation.violation_type.value}",
            user_id=violation.affected_user_id,
            result="blocked",
            security_context={
                "violation_id": violation.violation_id,
                "violation_type": violation.violation_type.value,
                "threat_level": violation.threat_level.value,
                "source_component": violation.source_component,
                "requesting_user_id": violation.requesting_user_id
            },
            metadata=violation.violation_details
        )
        
        with self._lock:
            self._audit_events.append(audit_event)
            self._audit_stats['events_logged'] += 1
            self._audit_stats['security_violations'] += 1
            self._audit_stats['blocked_operations'] += 1
            
            # Write to file immediately for security violations
            if self._audit_file_path:
                self._write_audit_event_to_file(audit_event)
        
        logger.error(f" ALERT:  SECURITY AUDIT: {violation.violation_type.value} - "
                    f"threat_level={violation.threat_level.value} (event_id: {audit_event.event_id})")
        
        return audit_event.event_id
    
    def _write_audit_event_to_file(self, event: AuditEvent):
        """Write audit event to file."""
        if not self._audit_file_path:
            return
        
        try:
            audit_data = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "user_id": event.user_id,
                "session_id": event.session_id,
                "operation": event.operation,
                "result": event.result,
                "security_context": event.security_context,
                "metadata": event.metadata
            }
            
            # Append to audit file
            with open(self._audit_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(audit_data) + '\n')
        
        except Exception as e:
            logger.error(f"Failed to write audit event to file: {e}")
    
    def get_audit_trail(self, user_id: Optional[str] = None, limit: int = 100) -> List[AuditEvent]:
        """Get audit trail for analysis.
        
        Args:
            user_id: Optional filter by user ID
            limit: Maximum number of events to return
            
        Returns:
            List of audit events
        """
        with self._lock:
            if user_id:
                filtered_events = [event for event in self._audit_events if event.user_id == user_id]
            else:
                filtered_events = self._audit_events
            
            return filtered_events[-limit:]
    
    def get_audit_statistics(self) -> Dict[str, Any]:
        """Get audit statistics."""
        with self._lock:
            uptime = (datetime.now(timezone.utc) - self._audit_stats['start_time']).total_seconds()
            
            return {
                **self._audit_stats,
                'uptime_seconds': uptime,
                'events_per_hour': (
                    (self._audit_stats['events_logged'] / uptime) * 3600
                    if uptime > 0 else 0
                ),
                'violation_rate': (
                    self._audit_stats['security_violations'] / 
                    max(1, self._audit_stats['events_logged'])
                ),
                'success_rate': (
                    self._audit_stats['successful_operations'] /
                    max(1, self._audit_stats['events_logged'])
                )
            }


# Global instances for the application
_security_validator: Optional[WebSocketSecurityValidator] = None
_audit_logger: Optional[WebSocketAuditLogger] = None
_lock = threading.Lock()


def get_security_validator() -> WebSocketSecurityValidator:
    """Get the global WebSocket security validator."""
    global _security_validator
    if _security_validator is None:
        with _lock:
            if _security_validator is None:
                _security_validator = WebSocketSecurityValidator()
    return _security_validator


def get_audit_logger() -> WebSocketAuditLogger:
    """Get the global WebSocket audit logger."""
    global _audit_logger
    if _audit_logger is None:
        with _lock:
            if _audit_logger is None:
                # Create audit file path in logs directory
                audit_file_path = Path("logs") / "websocket_security_audit.jsonl"
                audit_file_path.parent.mkdir(exist_ok=True)
                _audit_logger = WebSocketAuditLogger(str(audit_file_path))
    return _audit_logger


def validate_and_audit_websocket_operation(
    operation: str,
    user_context: UserExecutionContext,
    additional_validation: Optional[callable] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[str]]:
    """Validate and audit a WebSocket operation.
    
    Args:
        operation: Operation being performed
        user_context: User execution context
        additional_validation: Optional additional validation function
        metadata: Optional metadata for audit
        
    Returns:
        Tuple of (is_allowed, event_id)
    """
    validator = get_security_validator()
    auditor = get_audit_logger()
    
    # Validate user context isolation
    is_valid, violation = validator.validate_user_context_isolation(user_context, operation)
    
    if not is_valid:
        # Log security violation
        event_id = auditor.log_security_violation(violation)
        
        # Also log the blocked operation
        auditor.log_websocket_operation(
            operation=operation,
            user_id=user_context.user_id,
            result="blocked",
            security_context={"violation_id": violation.violation_id},
            metadata=metadata
        )
        
        return False, event_id
    
    # Perform additional validation if provided
    if additional_validation:
        try:
            additional_result = additional_validation()
            if not additional_result:
                event_id = auditor.log_websocket_operation(
                    operation=operation,
                    user_id=user_context.user_id,
                    result="blocked",
                    security_context={"reason": "additional_validation_failed"},
                    metadata=metadata
                )
                return False, event_id
        except Exception as e:
            event_id = auditor.log_websocket_operation(
                operation=operation,
                user_id=user_context.user_id,
                result="failure",
                security_context={"error": str(e)},
                metadata=metadata
            )
            return False, event_id
    
    # Operation is allowed - audit the success
    event_id = auditor.log_websocket_operation(
        operation=operation,
        user_id=user_context.user_id,
        result="success",
        metadata=metadata
    )
    
    return True, event_id


def get_security_dashboard_data() -> Dict[str, Any]:
    """Get security dashboard data for monitoring."""
    validator = get_security_validator()
    auditor = get_audit_logger()
    
    return {
        "security_metrics": validator.get_security_metrics(),
        "audit_statistics": auditor.get_audit_statistics(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }