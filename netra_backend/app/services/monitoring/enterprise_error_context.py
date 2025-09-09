"""Enterprise Error Context Management for GCP Error Reporting.

This module provides comprehensive business context preservation for enterprise-grade
error reporting, including customer tier analysis, performance correlation, and
compliance tracking.

Business Value Justification (BVJ):
1. Segment: Enterprise & Enterprise_Plus customers
2. Business Goal: Complete enterprise monitoring with business impact correlation
3. Value Impact: Enables business-driven error prioritization and SLA monitoring
4. Revenue Impact: Supports enterprise compliance requirements and premium monitoring features
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from shared.types import StronglyTypedUserExecutionContext, UserID
from netra_backend.app.schemas.monitoring_schemas import ErrorSeverity


@dataclass
class CompleteErrorContext:
    """Complete error context for enterprise-grade reporting."""
    
    # User Context
    user_id: str
    user_email: str
    customer_tier: str
    session_id: Optional[str]
    
    # Authentication Context
    jwt_token_id: Optional[str]
    auth_method: str
    permissions: List[str]
    auth_timestamp: Optional[datetime]
    
    # Business Context
    business_unit: str
    operation_type: str
    business_impact_level: str
    revenue_affecting: bool
    
    # Technical Context
    service_name: str
    endpoint: str
    request_id: Optional[str]
    trace_id: Optional[str]
    correlation_id: Optional[str]
    
    # Performance Context
    operation_duration_ms: Optional[int]
    expected_duration_ms: Optional[int]
    sla_threshold_ms: Optional[int]
    performance_baseline: Dict[str, float]
    
    # Compliance Context
    compliance_requirements: List[str]
    data_classification: str
    gdpr_applicable: bool
    sox_required: bool


class EnterpriseErrorContextBuilder:
    """Builds comprehensive enterprise context for error reporting."""
    
    # Customer tier configuration
    CUSTOMER_TIERS = {
        "Enterprise_Plus": {
            "priority_multiplier": 10,
            "sla_ms": 100,
            "always_report": True,
            "compliance_required": ["SOX", "GDPR", "HIPAA"]
        },
        "Enterprise": {
            "priority_multiplier": 8,
            "sla_ms": 200,
            "always_report": True,
            "compliance_required": ["SOX", "GDPR"]
        },
        "Professional": {
            "priority_multiplier": 5,
            "sla_ms": 500,
            "always_report": False,
            "compliance_required": ["GDPR"]
        },
        "Starter": {
            "priority_multiplier": 2,
            "sla_ms": 1000,
            "always_report": False,
            "compliance_required": []
        },
        "Free": {
            "priority_multiplier": 1,
            "sla_ms": 2000,
            "always_report": False,
            "compliance_required": []
        }
    }
    
    def build_enterprise_context(
        self, 
        user_context: Optional[StronglyTypedUserExecutionContext],
        operation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build complete enterprise context for error reporting.
        
        Args:
            user_context: User execution context
            operation_context: Operation-specific context
            
        Returns:
            Complete enterprise context dictionary
        """
        if not user_context:
            return self._build_anonymous_context(operation_context)
        
        customer_config = self._get_customer_config(user_context.customer_tier)
        
        return {
            # Customer Context
            "customer_tier": user_context.customer_tier,
            "customer_segment": self._determine_customer_segment(user_context),
            "enterprise_customer": user_context.customer_tier in ["Enterprise", "Enterprise_Plus"],
            "priority_multiplier": customer_config["priority_multiplier"],
            "always_report_errors": customer_config["always_report"],
            
            # Business Context
            "business_unit": operation_context.get("business_unit", user_context.business_unit),
            "business_impact": self._assess_business_impact(operation_context, user_context),
            "revenue_affecting": operation_context.get("revenue_affecting", False),
            "account_value": self._estimate_account_value(user_context),
            
            # Compliance Context
            "compliance_level": user_context.compliance_requirements,
            "sox_required": "SOX" in user_context.compliance_requirements,
            "gdpr_applicable": self._is_gdpr_applicable(user_context),
            "hipaa_applicable": "HIPAA" in user_context.compliance_requirements,
            "data_classification": operation_context.get("data_classification", "internal"),
            "audit_required": self._determine_audit_requirement(user_context),
            
            # Performance Context
            "sla_tier": self._get_sla_tier(user_context),
            "sla_threshold_ms": customer_config["sla_ms"],
            "performance_baseline": operation_context.get("expected_duration_ms"),
            "actual_duration": operation_context.get("actual_duration_ms"),
            "performance_degradation_pct": self._calculate_performance_degradation(operation_context),
            
            # Operational Context
            "operation_type": operation_context.get("operation_type", "unknown"),
            "api_endpoint": operation_context.get("endpoint"),
            "user_agent": operation_context.get("user_agent"),
            "trace_id": operation_context.get("trace_id"),
            "correlation_id": operation_context.get("correlation_id"),
            
            # User Context
            "user_id": user_context.user_id.value,
            "user_email": user_context.user_email,
            "session_id": user_context.session_id,
            "isolation_boundary": f"user-{user_context.user_id.value}"
        }
    
    def _build_anonymous_context(self, operation_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build context for anonymous users."""
        return {
            "customer_tier": "anonymous",
            "customer_segment": "anonymous",
            "enterprise_customer": False,
            "priority_multiplier": 1,
            "always_report_errors": False,
            "business_unit": operation_context.get("business_unit", "platform"),
            "business_impact": "low",
            "revenue_affecting": False,
            "compliance_level": [],
            "sox_required": False,
            "gdpr_applicable": False,
            "hipaa_applicable": False,
            "audit_required": False,
            "sla_tier": "basic",
            "sla_threshold_ms": 5000,
            "operation_type": operation_context.get("operation_type", "unknown")
        }
    
    def _get_customer_config(self, customer_tier: str) -> Dict[str, Any]:
        """Get configuration for customer tier."""
        return self.CUSTOMER_TIERS.get(customer_tier, self.CUSTOMER_TIERS["Free"])
    
    def _determine_customer_segment(self, user_context: StronglyTypedUserExecutionContext) -> str:
        """Determine customer segment for business analysis."""
        tier = user_context.customer_tier
        if tier in ["Enterprise_Plus", "Enterprise"]:
            return "enterprise"
        elif tier == "Professional":
            return "professional"
        elif tier == "Starter":
            return "startup"
        else:
            return "individual"
    
    def _assess_business_impact(
        self, 
        operation_context: Dict[str, Any], 
        user_context: StronglyTypedUserExecutionContext
    ) -> str:
        """Assess business impact level of the operation."""
        # High impact for enterprise customers
        if user_context.customer_tier in ["Enterprise_Plus", "Enterprise"]:
            return "high"
        
        # High impact for revenue-affecting operations
        if operation_context.get("revenue_affecting", False):
            return "high"
        
        # Medium impact for professional customers
        if user_context.customer_tier == "Professional":
            return "medium"
        
        # Check operation type
        operation_type = operation_context.get("operation_type", "")
        if operation_type in ["payment", "billing", "authentication"]:
            return "high"
        elif operation_type in ["user_management", "data_processing"]:
            return "medium"
        else:
            return "low"
    
    def _estimate_account_value(self, user_context: StronglyTypedUserExecutionContext) -> str:
        """Estimate account value tier for business prioritization."""
        tier_values = {
            "Enterprise_Plus": "high_value",
            "Enterprise": "high_value",
            "Professional": "medium_value",
            "Starter": "low_value",
            "Free": "no_value"
        }
        return tier_values.get(user_context.customer_tier, "no_value")
    
    def _is_gdpr_applicable(self, user_context: StronglyTypedUserExecutionContext) -> bool:
        """Determine if GDPR applies to this user."""
        # Check explicit compliance requirements
        if "GDPR" in user_context.compliance_requirements:
            return True
        
        # Check if user has region information indicating EU/UK
        if hasattr(user_context, 'region'):
            return user_context.region in ["EU", "UK"]
        
        return False
    
    def _determine_audit_requirement(self, user_context: StronglyTypedUserExecutionContext) -> bool:
        """Determine if audit logging is required."""
        return bool(user_context.compliance_requirements) or user_context.customer_tier in ["Enterprise_Plus", "Enterprise"]
    
    def _get_sla_tier(self, user_context: StronglyTypedUserExecutionContext) -> str:
        """Get SLA tier for customer."""
        tier_sla = {
            "Enterprise_Plus": "premium",
            "Enterprise": "premium", 
            "Professional": "standard",
            "Starter": "basic",
            "Free": "basic"
        }
        return tier_sla.get(user_context.customer_tier, "basic")
    
    def _calculate_performance_degradation(self, operation_context: Dict[str, Any]) -> Optional[float]:
        """Calculate performance degradation percentage."""
        actual = operation_context.get("actual_duration_ms")
        expected = operation_context.get("expected_duration_ms")
        
        if actual and expected and expected > 0:
            return ((actual - expected) / expected) * 100
        
        return None


class PerformanceErrorCorrelator:
    """Correlates errors with performance impact and SLA breaches."""
    
    def analyze_performance_impact(
        self, 
        error: Exception, 
        operation_context: Dict[str, Any],
        customer_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze performance impact of error.
        
        Args:
            error: Exception that occurred
            operation_context: Context of the operation
            customer_context: Customer-specific context
            
        Returns:
            Performance impact analysis
        """
        actual_duration = operation_context.get("actual_duration_ms", 0)
        expected_duration = operation_context.get("expected_duration_ms", 0)
        sla_threshold = customer_context.get("sla_threshold_ms", 1000)
        
        performance_impact = {
            "duration_ms": actual_duration,
            "expected_ms": expected_duration,
            "sla_threshold_ms": sla_threshold,
            "sla_breach": actual_duration > sla_threshold,
            "performance_degradation_pct": self._calculate_degradation(
                actual_duration, expected_duration
            ),
            "customer_impact_level": self._assess_customer_impact(
                actual_duration, sla_threshold, customer_context
            ),
            "error_type": type(error).__name__,
            "error_category": self._categorize_error(error),
            "recovery_time_estimate_ms": self._estimate_recovery_time(error, customer_context)
        }
        
        return performance_impact
    
    def _calculate_degradation(self, actual: int, expected: int) -> Optional[float]:
        """Calculate performance degradation percentage."""
        if expected > 0:
            return ((actual - expected) / expected) * 100
        return None
    
    def _assess_customer_impact(
        self, 
        actual_duration: int, 
        sla_threshold: int, 
        customer_context: Dict[str, Any]
    ) -> str:
        """Assess customer impact level."""
        if actual_duration > sla_threshold * 2:
            return "critical"
        elif actual_duration > sla_threshold:
            return "high" if customer_context.get("enterprise_customer") else "medium"
        else:
            return "low"
    
    def _categorize_error(self, error: Exception) -> str:
        """Categorize error by type."""
        error_name = type(error).__name__.lower()
        
        if "timeout" in error_name or "connectionerror" in error_name:
            return "connectivity"
        elif "authentication" in error_name or "authorization" in error_name:
            return "security"
        elif "validation" in error_name or "valueerror" in error_name:
            return "validation"
        elif "database" in error_name or "sql" in error_name:
            return "database"
        else:
            return "application"
    
    def _estimate_recovery_time(self, error: Exception, customer_context: Dict[str, Any]) -> int:
        """Estimate recovery time in milliseconds."""
        error_category = self._categorize_error(error)
        is_enterprise = customer_context.get("enterprise_customer", False)
        
        base_times = {
            "connectivity": 5000,  # 5 seconds
            "database": 10000,     # 10 seconds
            "security": 100,       # 100ms (fast fail)
            "validation": 100,     # 100ms (fast fail)
            "application": 2000    # 2 seconds
        }
        
        base_time = base_times.get(error_category, 2000)
        
        # Enterprise customers get faster recovery
        if is_enterprise:
            base_time = int(base_time * 0.5)
        
        return base_time


class ComplianceContextTracker:
    """Tracks compliance-related context for error reporting."""
    
    def build_compliance_context(
        self, 
        user_context: Optional[StronglyTypedUserExecutionContext],
        operation_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build compliance context for error reporting.
        
        Args:
            user_context: User execution context
            operation_context: Operation context
            
        Returns:
            Compliance context dictionary
        """
        if not user_context:
            return self._build_anonymous_compliance_context()
        
        compliance_context = {
            "gdpr_applicable": self._is_gdpr_applicable(user_context),
            "sox_required": "SOX" in user_context.compliance_requirements,
            "hipaa_applicable": "HIPAA" in user_context.compliance_requirements,
            "data_classification": operation_context.get("data_classification", "internal"),
            "pii_involved": operation_context.get("contains_pii", False),
            "audit_required": self._determine_audit_requirement(user_context),
            "retention_period_days": self._get_retention_period(user_context),
            "compliance_officer_notify": self._should_notify_compliance(
                user_context, operation_context
            ),
            "data_residency_requirements": self._get_data_residency_requirements(user_context),
            "encryption_required": self._is_encryption_required(user_context, operation_context)
        }
        
        return compliance_context
    
    def _build_anonymous_compliance_context(self) -> Dict[str, Any]:
        """Build compliance context for anonymous users."""
        return {
            "gdpr_applicable": False,
            "sox_required": False,
            "hipaa_applicable": False,
            "data_classification": "public",
            "pii_involved": False,
            "audit_required": False,
            "retention_period_days": 30,
            "compliance_officer_notify": False,
            "data_residency_requirements": [],
            "encryption_required": False
        }
    
    def _is_gdpr_applicable(self, user_context: StronglyTypedUserExecutionContext) -> bool:
        """Check if GDPR applies."""
        return "GDPR" in user_context.compliance_requirements or \
               (hasattr(user_context, 'region') and user_context.region in ["EU", "UK"])
    
    def _determine_audit_requirement(self, user_context: StronglyTypedUserExecutionContext) -> bool:
        """Determine if audit is required."""
        return bool(user_context.compliance_requirements) or \
               user_context.customer_tier in ["Enterprise", "Enterprise_Plus"]
    
    def _get_retention_period(self, user_context: StronglyTypedUserExecutionContext) -> int:
        """Get data retention period in days."""
        if "SOX" in user_context.compliance_requirements:
            return 2555  # 7 years for SOX
        elif "GDPR" in user_context.compliance_requirements:
            return 1095  # 3 years for GDPR
        elif user_context.customer_tier in ["Enterprise", "Enterprise_Plus"]:
            return 365   # 1 year for enterprise
        else:
            return 90    # 3 months default
    
    def _should_notify_compliance(
        self, 
        user_context: StronglyTypedUserExecutionContext,
        operation_context: Dict[str, Any]
    ) -> bool:
        """Determine if compliance officer should be notified."""
        # Notify for high-severity compliance-related errors
        if operation_context.get("contains_pii", False) and \
           ("GDPR" in user_context.compliance_requirements or "HIPAA" in user_context.compliance_requirements):
            return True
        
        # Notify for SOX-related errors
        if "SOX" in user_context.compliance_requirements and \
           operation_context.get("business_impact_level") == "high":
            return True
        
        return False
    
    def _get_data_residency_requirements(self, user_context: StronglyTypedUserExecutionContext) -> List[str]:
        """Get data residency requirements."""
        requirements = []
        
        if hasattr(user_context, 'region'):
            if user_context.region == "EU":
                requirements.append("eu_data_residency")
            elif user_context.region == "UK":
                requirements.append("uk_data_residency")
        
        if "GDPR" in user_context.compliance_requirements:
            requirements.append("gdpr_compliant_storage")
        
        return requirements
    
    def _is_encryption_required(
        self, 
        user_context: StronglyTypedUserExecutionContext,
        operation_context: Dict[str, Any]
    ) -> bool:
        """Determine if encryption is required."""
        # Encryption required for PII
        if operation_context.get("contains_pii", False):
            return True
        
        # Encryption required for compliance
        if user_context.compliance_requirements:
            return True
        
        # Encryption required for enterprise customers
        if user_context.customer_tier in ["Enterprise", "Enterprise_Plus"]:
            return True
        
        return False


# Factory functions for easy integration
def create_enterprise_error_context_builder() -> EnterpriseErrorContextBuilder:
    """Create enterprise error context builder."""
    return EnterpriseErrorContextBuilder()


def create_performance_error_correlator() -> PerformanceErrorCorrelator:
    """Create performance error correlator."""
    return PerformanceErrorCorrelator()


def create_compliance_context_tracker() -> ComplianceContextTracker:
    """Create compliance context tracker."""
    return ComplianceContextTracker()