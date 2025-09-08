"""
Deprecated pattern exceptions for Phase 1 remediation foundation.

These exceptions provide structured error handling for detecting and blocking
deprecated patterns, enabling systematic migration to SSOT-compliant architectures.

Business Value:
- Prevents technical debt accumulation through early detection
- Enforces SSOT compliance and modern architecture patterns
- Provides clear migration guidance for deprecated components
- Maintains system evolution towards business-focused naming and organization
"""

from typing import Any, Dict, Optional, List
from datetime import datetime, timezone

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity


class DeprecatedGlobalToolDispatcherError(NetraException):
    """
    Exception for deprecated global tool dispatcher usage.
    
    Enforces migration from global singletons to request-scoped tool dispatchers.
    Critical for multi-user isolation and preventing shared state contamination.
    
    Business Impact: Global state = user data leakage = security/privacy violations
    Recovery Guidance: Use BaseAgent.create_agent_with_context() factory pattern
    """
    
    def __init__(
        self,
        agent_name: str,
        initialization_location: str = None,
        run_id: str = None,
        user_id: str = None,
        context: Optional[Dict[str, Any]] = None
    ):
        error_context = context or {}
        error_context.update({
            "agent_name": agent_name,
            "initialization_location": initialization_location,
            "run_id": run_id,
            "user_id": user_id,
            "deprecated_pattern": "global_tool_dispatcher",
            "modern_alternative": "request_scoped_tool_dispatcher",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "isolation_risk": "high_user_contamination_risk"
        })
        
        business_message = (
            f"Agent '{agent_name}' initialized with deprecated global tool_dispatcher. "
            f"This violates multi-user isolation requirements."
        )
        
        user_message = (
            f"System detected deprecated initialization pattern. "
            f"Your session is isolated, but modernization is required for optimal performance."
        )
        
        super().__init__(
            message=business_message,
            code=ErrorCode.CONFIGURATION_ERROR,
            severity=ErrorSeverity.HIGH,  # HIGH because isolation is critical
            details={
                "isolation_impact": "Risk of user data contamination between sessions",
                "migration_required": True,
                "migration_steps": [
                    "Replace direct BaseAgent() initialization",
                    "Use BaseAgent.create_agent_with_context() factory",
                    "Pass user-scoped context to factory method",
                    "Verify request-scoped tool dispatcher creation",
                    "Test multi-user isolation thoroughly"
                ],
                "code_examples": {
                    "deprecated": "BaseAgent(tool_dispatcher=global_dispatcher)",
                    "modern": "BaseAgent.create_agent_with_context(user_context, run_id)"
                }
            },
            user_message=user_message,
            context=error_context
        )


class DeprecatedFactoryPatternError(NetraException):
    """
    Exception for deprecated factory pattern usage.
    
    Enforces migration from multiple factory implementations to unified SSOT factories.
    Critical for reducing over-engineering and maintaining architectural simplicity.
    
    Business Impact: Factory proliferation = complexity debt = slower development
    Recovery Guidance: Consolidate to unified factory patterns per SSOT principles
    """
    
    def __init__(
        self,
        factory_class: str,
        factory_type: str,
        recommended_replacement: str = None,
        usage_count: int = None,
        duplicate_factories: List[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        error_context = context or {}
        error_context.update({
            "factory_class": factory_class,
            "factory_type": factory_type,
            "recommended_replacement": recommended_replacement,
            "usage_count": usage_count,
            "duplicate_factories": duplicate_factories or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "architectural_debt": "high_complexity_overhead"
        })
        
        business_message = f"Deprecated factory pattern detected: {factory_class} ({factory_type})"
        if duplicate_factories:
            business_message += f" - {len(duplicate_factories)} similar factories exist"
        
        user_message = (
            f"System is using deprecated initialization patterns. "
            f"Functionality continues normally, but architectural improvements are recommended."
        )
        
        super().__init__(
            message=business_message,
            code=ErrorCode.CONFIGURATION_ERROR,
            severity=ErrorSeverity.MEDIUM,  # MEDIUM for architectural debt
            details={
                "architectural_impact": "Unnecessary complexity and maintenance overhead",
                "consolidation_required": True,
                "consolidation_steps": [
                    f"Identify all usages of {factory_class}",
                    f"Migrate to {recommended_replacement or 'unified factory pattern'}",
                    "Consolidate duplicate factory implementations",
                    "Update all consumers to use SSOT factory",
                    "Remove deprecated factory after migration",
                    "Validate no functionality regression"
                ],
                "ssot_principle": "One canonical factory per service type"
            },
            user_message=user_message,
            context=error_context
        )


class DeprecatedManagerPatternError(NetraException):
    """
    Exception for deprecated manager pattern usage.
    
    Enforces migration from multiple manager implementations to business-focused naming.
    Critical for reducing 154+ manager classes and improving code comprehension.
    
    Business Impact: Manager proliferation = confusion + maintenance overhead
    Recovery Guidance: Migrate to business-focused naming (Executor, Service, Handler, etc.)
    """
    
    def __init__(
        self,
        manager_class: str,
        business_function: str = None,
        recommended_name: str = None,
        similar_managers: List[str] = None,
        consolidation_candidate: bool = False,
        context: Optional[Dict[str, Any]] = None
    ):
        error_context = context or {}
        error_context.update({
            "manager_class": manager_class,
            "business_function": business_function,
            "recommended_name": recommended_name,
            "similar_managers": similar_managers or [],
            "consolidation_candidate": consolidation_candidate,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "naming_debt": "high_comprehension_overhead"
        })
        
        business_message = f"Deprecated manager pattern detected: {manager_class}"
        if business_function:
            business_message += f" (handles {business_function})"
        
        user_message = (
            f"System is using legacy naming patterns. "
            f"Functionality continues normally, but modernization improves maintainability."
        )
        
        severity = ErrorSeverity.HIGH if consolidation_candidate else ErrorSeverity.MEDIUM
        
        super().__init__(
            message=business_message,
            code=ErrorCode.CONFIGURATION_ERROR,
            severity=severity,
            details={
                "naming_impact": "Reduces code comprehension and increases cognitive load",
                "business_focused_naming_required": True,
                "migration_options": {
                    "executor": "For execution/orchestration logic",
                    "service": "For business logic processing", 
                    "handler": "For event/request handling",
                    "coordinator": "For multi-component coordination",
                    "validator": "For validation logic",
                    "processor": "For data processing"
                },
                "migration_steps": [
                    f"Analyze {manager_class} business function",
                    f"Choose appropriate business-focused name",
                    f"Rename class to {recommended_name or 'business-appropriate name'}",
                    "Update all imports and references",
                    "Consolidate with similar classes if possible",
                    "Update documentation and comments"
                ]
            },
            user_message=user_message,
            context=error_context
        )