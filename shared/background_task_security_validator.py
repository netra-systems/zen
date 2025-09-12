"""Background Task Security Validator

SECURITY CRITICAL: This module provides comprehensive validation to ensure all background
tasks maintain proper UserExecutionContext isolation and prevent data leakage.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Validate security compliance in background processing
- Value Impact: Prevents security violations and ensures audit compliance
- Revenue Impact: Maintains user trust and prevents data breaches

Key Security Features:
- Runtime validation of context presence in background tasks
- Detection of context-free background operations
- Audit trail generation for security compliance
- Automatic remediation suggestions for violations
- Performance monitoring for context validation overhead

Architecture:
This validator acts as a security gatekeeper for all background task operations,
ensuring that user context isolation is maintained throughout the system.
"""

import asyncio
import logging
import inspect
import traceback
import json
from typing import Any, Dict, List, Optional, Callable, Set, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError

logger = logging.getLogger(__name__)


class SecurityViolationType(str, Enum):
    """Types of security violations in background tasks."""
    MISSING_CONTEXT = "missing_context"
    INVALID_CONTEXT = "invalid_context"
    CONTEXT_MISMATCH = "context_mismatch"
    CONTEXT_TAMPERING = "context_tampering"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    ISOLATION_BREACH = "isolation_breach"


@dataclass
class SecurityViolation:
    """Represents a security violation in background task processing."""
    violation_type: SecurityViolationType
    task_name: str
    task_id: str
    user_id: Optional[str]
    description: str
    stack_trace: str
    timestamp: datetime
    remediation_suggestion: str
    severity: str = "HIGH"  # HIGH, MEDIUM, LOW
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary for logging/reporting."""
        return {
            'violation_type': self.violation_type,
            'task_name': self.task_name,
            'task_id': self.task_id,
            'user_id': self.user_id,
            'description': self.description,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity,
            'remediation_suggestion': self.remediation_suggestion,
            'stack_trace_hash': hash(self.stack_trace) % 1000000  # Truncated for privacy
        }


class BackgroundTaskSecurityValidator:
    """Comprehensive security validator for background task operations."""
    
    def __init__(self, enforce_strict_mode: bool = True):
        """Initialize security validator.
        
        Args:
            enforce_strict_mode: If True, raises exceptions on violations.
                               If False, logs violations but continues.
        """
        self.enforce_strict_mode = enforce_strict_mode
        self.violations: List[SecurityViolation] = []
        self.whitelisted_tasks: Set[str] = set()
        self.validation_stats = {
            'validations_performed': 0,
            'violations_detected': 0,
            'contexts_validated': 0,
            'tasks_validated': 0
        }
        
        logger.info(f"BackgroundTaskSecurityValidator initialized (strict_mode={enforce_strict_mode})")
    
    def whitelist_task(self, task_name: str, reason: str):
        """Whitelist a task that legitimately doesn't need user context.
        
        Args:
            task_name: Name of the task to whitelist
            reason: Reason why this task doesn't need user context
        """
        self.whitelisted_tasks.add(task_name)
        logger.info(f"Whitelisted task '{task_name}' for user context exemption: {reason}")
    
    def validate_background_task_context(
        self,
        task_name: str,
        task_id: str,
        user_context: Optional[UserExecutionContext] = None,
        require_context: bool = True,
        expected_user_id: Optional[str] = None
    ) -> bool:
        """Validate that a background task has proper user context isolation.
        
        Args:
            task_name: Name of the background task
            task_id: Unique identifier for the task instance
            user_context: UserExecutionContext for the task
            require_context: Whether context is required for this task
            expected_user_id: Expected user ID for validation
            
        Returns:
            True if validation passes
            
        Raises:
            InvalidContextError: If validation fails and strict mode is enabled
        """
        self.validation_stats['validations_performed'] += 1
        self.validation_stats['tasks_validated'] += 1
        
        try:
            # Check if task is whitelisted
            if not require_context and task_name in self.whitelisted_tasks:
                logger.debug(f"Task {task_name} is whitelisted for context exemption")
                return True
            
            # Validate context presence
            if require_context and user_context is None:
                violation = SecurityViolation(
                    violation_type=SecurityViolationType.MISSING_CONTEXT,
                    task_name=task_name,
                    task_id=task_id,
                    user_id=expected_user_id,
                    description=f"Background task '{task_name}' missing required UserExecutionContext",
                    stack_trace=self._get_stack_trace(),
                    timestamp=datetime.now(timezone.utc),
                    remediation_suggestion=(
                        f"Pass UserExecutionContext to task '{task_name}' or add to whitelist "
                        "if context is not needed"
                    )
                )
                return self._handle_violation(violation)
            
            # Validate context if present
            if user_context is not None:
                self.validation_stats['contexts_validated'] += 1
                
                # Validate context integrity
                try:
                    user_context.verify_isolation()
                except Exception as e:
                    violation = SecurityViolation(
                        violation_type=SecurityViolationType.INVALID_CONTEXT,
                        task_name=task_name,
                        task_id=task_id,
                        user_id=user_context.user_id if hasattr(user_context, 'user_id') else None,
                        description=f"Invalid UserExecutionContext in task '{task_name}': {e}",
                        stack_trace=self._get_stack_trace(),
                        timestamp=datetime.now(timezone.utc),
                        remediation_suggestion="Ensure UserExecutionContext is properly constructed and not corrupted"
                    )
                    return self._handle_violation(violation)
                
                # Validate user ID match if expected
                if expected_user_id and user_context.user_id != expected_user_id:
                    violation = SecurityViolation(
                        violation_type=SecurityViolationType.CONTEXT_MISMATCH,
                        task_name=task_name,
                        task_id=task_id,
                        user_id=user_context.user_id,
                        description=(
                            f"User ID mismatch in task '{task_name}': "
                            f"expected {expected_user_id}, got {user_context.user_id}"
                        ),
                        stack_trace=self._get_stack_trace(),
                        timestamp=datetime.now(timezone.utc),
                        remediation_suggestion="Ensure correct UserExecutionContext is passed to the task"
                    )
                    return self._handle_violation(violation)
            
            logger.debug(f"Background task security validation passed: {task_name} (ID: {task_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error during security validation for task {task_name}: {e}")
            if self.enforce_strict_mode:
                raise
            return False
    
    def validate_task_function_signature(self, task_func: Callable, task_name: str) -> bool:
        """Validate that a task function can accept UserExecutionContext.
        
        Args:
            task_func: The task function to validate
            task_name: Name of the task for reporting
            
        Returns:
            True if function signature supports user context
        """
        try:
            sig = inspect.signature(task_func)
            
            # Check if function accepts user_context parameter
            has_context_param = 'user_context' in sig.parameters
            
            # Check if function accepts **kwargs (can receive context)
            has_kwargs = any(param.kind == param.VAR_KEYWORD for param in sig.parameters.values())
            
            if not has_context_param and not has_kwargs:
                logger.warning(
                    f"Task function '{task_name}' doesn't accept user_context parameter. "
                    "Consider adding 'user_context: Optional[UserExecutionContext] = None' parameter."
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating task function signature for {task_name}: {e}")
            return False
    
    def audit_background_task_call(
        self,
        task_name: str,
        task_args: tuple,
        task_kwargs: Dict[str, Any],
        caller_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Audit a background task call for security compliance.
        
        Args:
            task_name: Name of the task being called
            task_args: Positional arguments to the task
            task_kwargs: Keyword arguments to the task
            caller_context: Optional information about the caller
            
        Returns:
            Audit information dictionary
        """
        audit_info = {
            'task_name': task_name,
            'has_user_context': 'user_context' in task_kwargs,
            'context_user_id': None,
            'caller_context': caller_context,
            'args_count': len(task_args),
            'kwargs_keys': list(task_kwargs.keys()),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'security_compliant': False
        }
        
        # Extract user context if present
        user_context = task_kwargs.get('user_context')
        if user_context and isinstance(user_context, UserExecutionContext):
            audit_info['context_user_id'] = user_context.user_id
            audit_info['context_request_id'] = user_context.request_id
            audit_info['security_compliant'] = True
        
        # Log audit information
        logger.info(f"Background task audit: {json.dumps(audit_info)}")
        
        return audit_info
    
    def get_violation_summary(self) -> Dict[str, Any]:
        """Get summary of security violations detected."""
        violation_counts = {}
        for violation in self.violations:
            violation_type = violation.violation_type
            violation_counts[violation_type] = violation_counts.get(violation_type, 0) + 1
        
        return {
            'total_violations': len(self.violations),
            'violation_types': violation_counts,
            'validation_stats': self.validation_stats.copy(),
            'recent_violations': [v.to_dict() for v in self.violations[-5:]]  # Last 5 violations
        }
    
    def generate_security_report(self) -> str:
        """Generate comprehensive security report."""
        summary = self.get_violation_summary()
        
        report = [
            "BACKGROUND TASK SECURITY REPORT",
            "=" * 50,
            f"Total Validations: {summary['validation_stats']['validations_performed']}",
            f"Total Violations: {summary['total_violations']}",
            f"Contexts Validated: {summary['validation_stats']['contexts_validated']}",
            f"Tasks Validated: {summary['validation_stats']['tasks_validated']}",
            "",
            "VIOLATION BREAKDOWN:"
        ]
        
        for violation_type, count in summary['violation_types'].items():
            report.append(f"  {violation_type}: {count}")
        
        report.extend([
            "",
            f"WHITELISTED TASKS: {len(self.whitelisted_tasks)}",
            *[f"  - {task}" for task in sorted(self.whitelisted_tasks)],
            "",
            "RECENT VIOLATIONS:"
        ])
        
        for violation in summary['recent_violations']:
            report.append(f"  [{violation['timestamp']}] {violation['task_name']}: {violation['description']}")
        
        return "\n".join(report)
    
    def clear_violations(self):
        """Clear stored violations (for testing/reset)."""
        self.violations.clear()
        logger.info("Cleared security violation history")
    
    def _handle_violation(self, violation: SecurityViolation) -> bool:
        """Handle a security violation.
        
        Args:
            violation: The security violation to handle
            
        Returns:
            False (validation failed)
            
        Raises:
            InvalidContextError: If strict mode is enabled
        """
        self.violations.append(violation)
        self.validation_stats['violations_detected'] += 1
        
        # Log violation
        logger.error(
            f"SECURITY VIOLATION: {violation.description} "
            f"(Type: {violation.violation_type}, Task: {violation.task_name})"
        )
        
        # Log remediation suggestion
        logger.info(f"REMEDIATION: {violation.remediation_suggestion}")
        
        if self.enforce_strict_mode:
            raise InvalidContextError(violation.description)
        
        return False
    
    def _get_stack_trace(self) -> str:
        """Get current stack trace for violation reporting."""
        return traceback.format_stack()[-5:].__str__()  # Last 5 frames


# Module-level validator instance
_global_validator = BackgroundTaskSecurityValidator()


def get_security_validator() -> BackgroundTaskSecurityValidator:
    """Get the global security validator instance."""
    return _global_validator


def validate_background_task(
    task_name: str,
    task_id: str,
    user_context: Optional[UserExecutionContext] = None,
    require_context: bool = True
) -> bool:
    """Convenience function for background task security validation."""
    return _global_validator.validate_background_task_context(
        task_name=task_name,
        task_id=task_id,
        user_context=user_context,
        require_context=require_context
    )


def security_required(task_name: str, require_context: bool = True):
    """Decorator for background tasks that require security validation.
    
    Args:
        task_name: Name of the task for validation
        require_context: Whether UserExecutionContext is required
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            # Extract user context and task ID
            user_context = kwargs.get('user_context')
            task_id = kwargs.get('task_id', f"{task_name}_{id(func)}")
            
            # Validate security
            validate_background_task(
                task_name=task_name,
                task_id=task_id,
                user_context=user_context,
                require_context=require_context
            )
            
            # Audit the call
            _global_validator.audit_background_task_call(
                task_name=task_name,
                task_args=args,
                task_kwargs=kwargs,
                caller_context="security_required_decorator"
            )
            
            # Execute the function
            return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            # Similar logic for synchronous functions
            user_context = kwargs.get('user_context')
            task_id = kwargs.get('task_id', f"{task_name}_{id(func)}")
            
            validate_background_task(
                task_name=task_name,
                task_id=task_id,
                user_context=user_context,
                require_context=require_context
            )
            
            _global_validator.audit_background_task_call(
                task_name=task_name,
                task_args=args,
                task_kwargs=kwargs,
                caller_context="security_required_decorator"
            )
            
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Export public classes and functions
__all__ = [
    'BackgroundTaskSecurityValidator',
    'SecurityViolation',
    'SecurityViolationType',
    'get_security_validator',
    'validate_background_task',
    'security_required'
]