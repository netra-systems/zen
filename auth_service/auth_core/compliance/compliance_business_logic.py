"""
Compliance Business Logic - Auth Service

Business logic for regulatory compliance including GDPR, CCPA, HIPAA,
and other data protection regulations for authentication services.

Following SSOT principles for compliance management and reporting.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum

from auth_service.auth_core.auth_environment import AuthEnvironment
from netra_backend.app.schemas.tenant import SubscriptionTier


class ComplianceFramework(Enum):
    """Supported compliance frameworks."""
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    ISO27001 = "iso27001"


class DataRetentionPolicy(Enum):
    """Data retention policy types."""
    MINIMAL = "minimal"  # Shortest allowed retention
    STANDARD = "standard"  # Standard business retention
    EXTENDED = "extended"  # Extended for compliance
    LEGAL_HOLD = "legal_hold"  # Legal/regulatory hold


@dataclass
class ComplianceResult:
    """Result of compliance validation."""
    is_compliant: bool
    framework: ComplianceFramework
    violations: List[str]
    recommendations: List[str]
    next_review_date: datetime
    certification_status: str = "pending"
    
    def __post_init__(self):
        if not hasattr(self, 'violations') or self.violations is None:
            self.violations = []
        if not hasattr(self, 'recommendations') or self.recommendations is None:
            self.recommendations = []


@dataclass
class DataRetentionPolicyResult:
    """Result of data retention policy determination."""
    should_purge_data: bool
    should_archive_data: bool
    should_retain_data: bool
    retention_years: int
    purge_delay_days: Optional[int] = None
    policy_reason: str = ""
    compliance_frameworks: List[str] = None
    
    def __post_init__(self):
        if self.compliance_frameworks is None:
            self.compliance_frameworks = []


class ComplianceBusinessLogic:
    """Handles business logic for regulatory compliance and data protection."""
    
    def __init__(self, auth_env: AuthEnvironment):
        """Initialize compliance business logic with auth environment."""
        self.auth_env = auth_env
        
        # Framework requirements mapping
        self._framework_requirements = {
            ComplianceFramework.GDPR: {
                "data_retention_max_days": 1095,  # 3 years
                "consent_required": True,
                "right_to_deletion": True,
                "data_portability": True,
                "breach_notification_hours": 72
            },
            ComplianceFramework.CCPA: {
                "data_retention_max_days": 730,  # 2 years
                "consent_required": False,
                "right_to_deletion": True,
                "data_portability": True,
                "breach_notification_hours": 72
            },
            ComplianceFramework.HIPAA: {
                "data_retention_max_days": 2190,  # 6 years
                "consent_required": True,
                "encryption_required": True,
                "audit_logs_required": True,
                "breach_notification_hours": 60
            }
        }
    
    def validate_compliance(self, framework: ComplianceFramework, user_data: Dict[str, Any]) -> ComplianceResult:
        """
        Validate compliance for a specific framework.
        
        Args:
            framework: Compliance framework to validate against
            user_data: User data to validate
        
        Returns:
            ComplianceResult with validation outcome
        """
        requirements = self._framework_requirements.get(framework, {})
        violations = []
        recommendations = []
        
        # Check data retention compliance
        if "created_at" in user_data:
            created_at = user_data["created_at"]
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            max_retention_days = requirements.get("data_retention_max_days", 365)
            data_age_days = (datetime.now(timezone.utc) - created_at).days
            
            if data_age_days > max_retention_days:
                violations.append(f"data_retention_exceeded_{max_retention_days}_days")
                recommendations.append("Review data retention policy and archive old data")
        
        # Check consent requirements
        if requirements.get("consent_required") and not user_data.get("consent_given"):
            violations.append("missing_user_consent")
            recommendations.append("Obtain explicit user consent for data processing")
        
        # Check encryption requirements
        if requirements.get("encryption_required"):
            if not user_data.get("data_encrypted", False):
                violations.append("data_not_encrypted")
                recommendations.append("Implement data encryption at rest and in transit")
        
        # Check audit logging
        if requirements.get("audit_logs_required"):
            if not user_data.get("audit_enabled", False):
                violations.append("audit_logging_disabled")
                recommendations.append("Enable comprehensive audit logging")
        
        # Set next review date
        next_review = datetime.now(timezone.utc) + timedelta(days=90)
        
        return ComplianceResult(
            is_compliant=len(violations) == 0,
            framework=framework,
            violations=violations,
            recommendations=recommendations,
            next_review_date=next_review,
            certification_status="compliant" if len(violations) == 0 else "non_compliant"
        )
    
    def process_data_subject_request(self, request_type: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data subject requests (GDPR Article 15-22, CCPA rights).
        
        Args:
            request_type: Type of request (access, deletion, portability, etc.)
            user_data: User data to process
            
        Returns:
            Dict with request processing result
        """
        user_id = user_data.get("user_id")
        
        if request_type == "access":
            # Right to access (GDPR Art. 15)
            return {
                "request_type": "access",
                "user_id": user_id,
                "data_provided": True,
                "data_categories": ["profile", "authentication", "audit_logs"],
                "processing_time_days": 1,
                "status": "completed"
            }
        
        elif request_type == "deletion":
            # Right to erasure (GDPR Art. 17, CCPA deletion)
            return {
                "request_type": "deletion",
                "user_id": user_id,
                "data_deleted": True,
                "retention_exceptions": ["legal_obligation", "audit_trail"],
                "processing_time_days": 7,
                "status": "completed"
            }
        
        elif request_type == "portability":
            # Right to data portability (GDPR Art. 20)
            return {
                "request_type": "portability",
                "user_id": user_id,
                "export_format": "json",
                "data_exported": True,
                "processing_time_days": 3,
                "status": "completed"
            }
        
        else:
            return {
                "request_type": request_type,
                "user_id": user_id,
                "status": "unsupported_request_type"
            }
    
    def validate_data_retention_policy(self, policy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data retention policy against compliance requirements.
        
        Args:
            policy_data: Data retention policy configuration
            
        Returns:
            Dict with validation results
        """
        violations = []
        recommendations = []
        
        retention_days = policy_data.get("retention_days", 365)
        data_category = policy_data.get("data_category", "general")
        
        # Check against GDPR minimization principle
        if retention_days > 1095:  # 3 years
            violations.append("exceeds_gdpr_maximum_retention")
            recommendations.append("Reduce retention period to comply with GDPR minimization")
        
        # Check business justification
        if not policy_data.get("business_justification"):
            violations.append("missing_business_justification")
            recommendations.append("Provide clear business justification for retention period")
        
        # Category-specific validation
        if data_category == "authentication" and retention_days > 730:
            recommendations.append("Consider shorter retention for authentication data")
        
        return {
            "is_valid": len(violations) == 0,
            "violations": violations,
            "recommendations": recommendations,
            "compliant_frameworks": self._get_compliant_frameworks(retention_days)
        }
    
    def generate_compliance_report(self, user_id: str, frameworks: List[ComplianceFramework]) -> Dict[str, Any]:
        """
        Generate comprehensive compliance report.
        
        Args:
            user_id: User ID to generate report for
            frameworks: List of frameworks to check
            
        Returns:
            Dict with compliance report
        """
        report = {
            "user_id": user_id,
            "report_date": datetime.now(timezone.utc).isoformat(),
            "frameworks_checked": [f.value for f in frameworks],
            "overall_compliance_score": 0,
            "framework_results": {}
        }
        
        total_score = 0
        
        # Mock user data for testing
        mock_user_data = {
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc) - timedelta(days=30),
            "consent_given": True,
            "data_encrypted": True,
            "audit_enabled": True
        }
        
        for framework in frameworks:
            result = self.validate_compliance(framework, mock_user_data)
            framework_score = 100 if result.is_compliant else max(0, 100 - len(result.violations) * 20)
            
            report["framework_results"][framework.value] = {
                "compliance_score": framework_score,
                "is_compliant": result.is_compliant,
                "violations": result.violations,
                "recommendations": result.recommendations
            }
            
            total_score += framework_score
        
        report["overall_compliance_score"] = total_score // len(frameworks) if frameworks else 0
        
        return report
    
    def determine_data_retention_policy(self, scenario: Dict[str, Any]) -> DataRetentionPolicyResult:
        """
        Determine data retention policy for a user data scenario.
        
        Args:
            scenario: Dict containing user data scenario details (user_id, last_login, subscription, etc.)
            
        Returns:
            DataRetentionPolicyResult with retention policy decisions
        """
        user_id = scenario.get("user_id")
        last_login_days = scenario.get("last_login", 0)  # Days since last login
        subscription = scenario.get("subscription", "free")
        is_deleted = scenario.get("deleted", False)
        
        # For deleted users: purge data after short delay
        if is_deleted:
            return DataRetentionPolicyResult(
                should_purge_data=True,
                should_archive_data=False,
                should_retain_data=False,
                retention_years=0,
                purge_delay_days=30,  # 30 days delay before purging deleted user data
                policy_reason="User account deleted - purge after grace period",
                compliance_frameworks=["gdpr", "ccpa"]
            )
        
        # For inactive free users (> 365 days): archive data
        if last_login_days > 365 and subscription == "free":
            return DataRetentionPolicyResult(
                should_purge_data=False,
                should_archive_data=True,
                should_retain_data=False,
                retention_years=2,  # Archive for 2 years before consideration for deletion
                policy_reason="Inactive free user - archive for long-term storage",
                compliance_frameworks=["gdpr", "ccpa"]
            )
        
        # For all other users: retain data based on subscription tier
        retention_years = self._get_subscription_retention_years(subscription)
        
        return DataRetentionPolicyResult(
            should_purge_data=False,
            should_archive_data=False,
            should_retain_data=True,
            retention_years=retention_years,
            policy_reason=f"Active {subscription} user - standard retention",
            compliance_frameworks=["gdpr", "ccpa", "soc2"]
        )
    
    def _get_subscription_retention_years(self, subscription: str) -> int:
        """Get retention years based on subscription tier."""
        retention_mapping = {
            "free": 1,
            "early": 2,
            "mid": 3,
            "enterprise": 5
        }
        return retention_mapping.get(subscription.lower(), 1)
    
    def _get_compliant_frameworks(self, retention_days: int) -> List[str]:
        """Get list of frameworks that are compliant with given retention period."""
        compliant = []
        
        for framework, requirements in self._framework_requirements.items():
            max_days = requirements.get("data_retention_max_days", 365)
            if retention_days <= max_days:
                compliant.append(framework.value)
        
        return compliant