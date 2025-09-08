"""
Agent-specific exceptions for Phase 1 remediation foundation.

These exceptions provide structured error handling for agent lifecycle, state management,
and context operations, enabling progression from warnings to errors while preserving
business value and execution integrity.

Business Value:
- Protects agent execution integrity and state consistency
- Enables progressive error escalation for agent lifecycle issues
- Provides diagnostic context for agent troubleshooting
- Maintains multi-user isolation and execution reliability
"""

from typing import Any, Dict, Optional, List
from datetime import datetime, timezone

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity


class AgentLifecycleError(NetraException):
    """
    Exception for agent lifecycle transition failures.
    
    Covers entry condition failures, state validation issues, and lifecycle violations.
    Critical for maintaining agent execution order and business logic integrity.
    
    Business Impact: Broken agent flows = incomplete AI responses = user frustration
    Recovery Guidance: Validate preconditions, check dependencies, ensure proper handoffs
    """
    
    def __init__(
        self,
        agent_name: str,
        lifecycle_phase: str,
        run_id: str = None,
        missing_conditions: List[str] = None,
        current_state: str = None,
        expected_state: str = None,
        context: Optional[Dict[str, Any]] = None
    ):
        error_context = context or {}
        error_context.update({
            "agent_name": agent_name,
            "lifecycle_phase": lifecycle_phase,
            "run_id": run_id,
            "missing_conditions": missing_conditions or [],
            "current_state": current_state,
            "expected_state": expected_state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "business_impact": "agent_execution_integrity_violation"
        })
        
        business_message = f"Agent '{agent_name}' lifecycle failure in {lifecycle_phase}"
        if missing_conditions:
            business_message += f" - missing conditions: {', '.join(missing_conditions)}"
        
        user_message = (
            f"AI agent execution encountered a setup issue. "
            f"This may result in incomplete or unexpected responses. "
            f"Please try your request again."
        )
        
        super().__init__(
            message=business_message,
            code=ErrorCode.AGENT_EXECUTION_FAILED,
            severity=ErrorSeverity.HIGH,  # HIGH because it affects execution integrity
            details={
                "business_impact": "May result in incomplete AI responses",
                "recovery_actions": [
                    "Validate agent entry conditions",
                    "Check required dependencies availability",
                    "Verify agent execution context integrity",
                    "Ensure proper agent handoff protocols",
                    "Review agent dependency chain"
                ]
            },
            user_message=user_message,
            context=error_context
        )


class AgentStateTransitionError(NetraException):
    """
    Exception for invalid agent state transitions.
    
    Covers state consistency violations and transition logic errors.
    Critical for maintaining system reliability and preventing corruption.
    
    Business Impact: State corruption = unpredictable system behavior
    Recovery Guidance: Reset to known good state, validate transition logic
    """
    
    def __init__(
        self,
        agent_name: str,
        from_state: str,
        to_state: str,
        transition_error: str,
        run_id: str = None,
        context: Optional[Dict[str, Any]] = None
    ):
        error_context = context or {}
        error_context.update({
            "agent_name": agent_name,
            "from_state": from_state,
            "to_state": to_state,
            "transition_error": transition_error,
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        business_message = (
            f"Agent '{agent_name}' invalid state transition: "
            f"{from_state} -> {to_state} - {transition_error}"
        )
        
        super().__init__(
            message=business_message,
            code=ErrorCode.INTERNAL_ERROR,
            severity=ErrorSeverity.CRITICAL,  # CRITICAL because state corruption is serious
            details={
                "recovery_actions": [
                    "Reset agent to known good state",
                    "Validate state transition logic",
                    "Check for race conditions",
                    "Verify state consistency rules",
                    "Review concurrent access patterns"
                ]
            },
            context=error_context
        )


class AgentContextError(NetraException):
    """
    Exception for agent context management failures.
    
    Covers context clearing, reset failures, and context corruption issues.
    Critical for multi-user isolation and preventing data leakage.
    
    Business Impact: Context leakage = security risk + incorrect responses
    Recovery Guidance: Force context reset, validate isolation boundaries
    """
    
    def __init__(
        self,
        agent_name: str,
        context_operation: str,
        error_details: str,
        run_id: str = None,
        user_id: str = None,
        isolation_breach: bool = False,
        context: Optional[Dict[str, Any]] = None
    ):
        error_context = context or {}
        error_context.update({
            "agent_name": agent_name,
            "context_operation": context_operation,
            "error_details": error_details,
            "run_id": run_id,
            "user_id": user_id,
            "isolation_breach": isolation_breach,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "security_impact": "high" if isolation_breach else "medium"
        })
        
        business_message = f"Agent '{agent_name}' context {context_operation} failed: {error_details}"
        
        severity = ErrorSeverity.CRITICAL if isolation_breach else ErrorSeverity.HIGH
        
        user_message = (
            f"Agent context management issue detected. "
            f"For security, this session will be reset. Please try your request again."
            if isolation_breach else
            f"Agent encountered a context issue. Your request may need to be retried."
        )
        
        super().__init__(
            message=business_message,
            code=ErrorCode.INTERNAL_ERROR,
            severity=severity,
            details={
                "security_impact": "Potential user isolation violation" if isolation_breach else "Context integrity issue",
                "recovery_actions": [
                    "Force agent context reset",
                    "Validate user isolation boundaries", 
                    "Check context cleanup procedures",
                    "Verify memory management",
                    "Review concurrent context access"
                ]
            },
            user_message=user_message,
            context=error_context
        )


class AgentRecoveryError(NetraException):
    """
    Exception for agent recovery operation failures.
    
    Covers circuit breaker resets, reliability manager failures, and recovery protocol errors.
    Critical for system resilience and graceful degradation.
    
    Business Impact: Failed recovery = system instability + cascading failures
    Recovery Guidance: Manual intervention may be required, escalate to operations
    """
    
    def __init__(
        self,
        agent_name: str,
        recovery_operation: str,
        failure_reason: str,
        run_id: str = None,
        recovery_attempts: int = None,
        context: Optional[Dict[str, Any]] = None
    ):
        error_context = context or {}
        error_context.update({
            "agent_name": agent_name,
            "recovery_operation": recovery_operation,
            "failure_reason": failure_reason,
            "run_id": run_id,
            "recovery_attempts": recovery_attempts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operational_impact": "high_system_instability_risk"
        })
        
        business_message = f"Agent '{agent_name}' recovery failed: {recovery_operation} - {failure_reason}"
        
        user_message = (
            f"AI agent recovery procedures encountered an issue. "
            f"System stability may be affected. Please contact support if problems persist."
        )
        
        super().__init__(
            message=business_message,
            code=ErrorCode.INTERNAL_ERROR,
            severity=ErrorSeverity.CRITICAL,  # CRITICAL because recovery failure is serious
            details={
                "operational_impact": "System instability and potential cascading failures",
                "recovery_actions": [
                    "Manual system health check required",
                    "Verify recovery protocol integrity",
                    "Check system resource availability",
                    "Review error logs for root cause",
                    "Consider service restart if persistent",
                    "Escalate to on-call team"
                ]
            },
            user_message=user_message,
            context=error_context
        )


class DeprecatedPatternError(NetraException):
    """
    Exception for deprecated pattern usage detection.
    
    Covers usage of deprecated factories, managers, and initialization patterns.
    Important for technical debt reduction and system modernization.
    
    Business Impact: Technical debt accumulation = reduced development velocity
    Recovery Guidance: Migrate to modern SSOT patterns immediately
    """
    
    def __init__(
        self,
        deprecated_pattern: str,
        modern_alternative: str,
        usage_location: str = None,
        migration_guide: str = None,
        context: Optional[Dict[str, Any]] = None
    ):
        error_context = context or {}
        error_context.update({
            "deprecated_pattern": deprecated_pattern,
            "modern_alternative": modern_alternative,
            "usage_location": usage_location,
            "migration_guide": migration_guide,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "technical_debt_impact": "high"
        })
        
        business_message = f"Deprecated pattern detected: {deprecated_pattern}"
        if usage_location:
            business_message += f" at {usage_location}"
        
        user_message = (
            f"System is using deprecated components. "
            f"Functionality continues normally, but modernization is recommended."
        )
        
        super().__init__(
            message=business_message,
            code=ErrorCode.CONFIGURATION_ERROR,
            severity=ErrorSeverity.MEDIUM,  # MEDIUM for technical debt
            details={
                "modernization_required": True,
                "migration_path": modern_alternative,
                "recovery_actions": [
                    f"Migrate from {deprecated_pattern} to {modern_alternative}",
                    "Update initialization patterns to SSOT compliance",
                    "Follow migration guides in docs/",
                    "Test thoroughly after migration",
                    "Remove legacy code after validation"
                ]
            },
            user_message=user_message,
            context=error_context
        )