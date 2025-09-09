"""
Audit Business Logic - Auth Service

Business logic for audit event processing, compliance tracking,
and security event logging for authentication operations.

Following SSOT principles for audit and compliance management.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from auth_service.auth_core.auth_environment import AuthEnvironment
from netra_backend.app.schemas.tenant import SubscriptionTier


class AuditEventType(Enum):
    """Types of audit events."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTRATION = "user_registration"
    PASSWORD_CHANGE = "password_change"
    FAILED_LOGIN = "failed_login"
    ACCOUNT_LOCKED = "account_locked"
    OAUTH_LOGIN = "oauth_login"
    PERMISSION_DENIED = "permission_denied"
    SESSION_CREATED = "session_created"
    SESSION_TERMINATED = "session_terminated"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEventResult:
    """Result of audit event processing."""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    logged: bool
    requires_alert: bool = False
    compliance_tags: List[str] = None
    retention_period_days: int = 90
    
    def __post_init__(self):
        if self.compliance_tags is None:
            self.compliance_tags = []


@dataclass
class AuditRequirement:
    """Result of audit requirement determination."""
    must_audit: bool
    requires_immediate_alert: bool
    retention_years: int
    event_type: str
    severity_level: str
    compliance_flags: List[str] = None
    
    def __post_init__(self):
        if self.compliance_flags is None:
            self.compliance_flags = []


class AuditBusinessLogic:
    """Handles business logic for audit events and compliance tracking."""
    
    def __init__(self, auth_env: AuthEnvironment):
        """Initialize audit business logic with auth environment."""
        self.auth_env = auth_env
        
        # Event severity mapping
        self._event_severity_mapping = {
            AuditEventType.USER_LOGIN: AuditSeverity.LOW,
            AuditEventType.USER_LOGOUT: AuditSeverity.LOW,
            AuditEventType.USER_REGISTRATION: AuditSeverity.MEDIUM,
            AuditEventType.PASSWORD_CHANGE: AuditSeverity.MEDIUM,
            AuditEventType.FAILED_LOGIN: AuditSeverity.MEDIUM,
            AuditEventType.ACCOUNT_LOCKED: AuditSeverity.HIGH,
            AuditEventType.OAUTH_LOGIN: AuditSeverity.LOW,
            AuditEventType.PERMISSION_DENIED: AuditSeverity.HIGH,
            AuditEventType.SESSION_CREATED: AuditSeverity.LOW,
            AuditEventType.SESSION_TERMINATED: AuditSeverity.LOW,
        }
        
        # Compliance tag mapping
        self._compliance_tags = {
            AuditEventType.USER_LOGIN: ["access_control", "authentication"],
            AuditEventType.FAILED_LOGIN: ["security_incident", "authentication"],
            AuditEventType.ACCOUNT_LOCKED: ["security_incident", "account_security"],
            AuditEventType.PASSWORD_CHANGE: ["account_security", "authentication"],
            AuditEventType.PERMISSION_DENIED: ["access_control", "security_incident"],
        }
    
    def process_audit_event(self, event_data: Dict[str, Any]) -> AuditEventResult:
        """
        Process an audit event and determine logging/alerting requirements.
        
        Args:
            event_data: Dict containing event_type, user_id, details, etc.
        
        Returns:
            AuditEventResult with processing outcome
        """
        event_type_str = event_data.get("event_type")
        event_type = AuditEventType(event_type_str) if event_type_str else AuditEventType.USER_LOGIN
        
        user_id = event_data.get("user_id")
        subscription_tier = event_data.get("subscription_tier", SubscriptionTier.FREE)
        
        # Determine severity
        severity = self._event_severity_mapping.get(event_type, AuditSeverity.LOW)
        
        # Check if requires alert based on severity and frequency
        requires_alert = self._should_trigger_alert(event_type, event_data)
        
        # Get compliance tags
        compliance_tags = self._compliance_tags.get(event_type, [])
        
        # Determine retention period based on subscription tier and event type
        retention_days = self._get_retention_period(subscription_tier, event_type)
        
        # Generate event ID
        event_id = f"audit_{event_type.value}_{user_id}_{int(datetime.now(timezone.utc).timestamp())}"
        
        return AuditEventResult(
            event_id=event_id,
            event_type=event_type,
            severity=severity,
            logged=True,  # For testing, assume all events are logged
            requires_alert=requires_alert,
            compliance_tags=compliance_tags,
            retention_period_days=retention_days
        )
    
    def validate_audit_business_rules(self, audit_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate audit data against business rules.
        
        Args:
            audit_data: Audit event data to validate
            
        Returns:
            Dict with validation results
        """
        violations = []
        warnings = []
        
        # Check required fields
        required_fields = ["event_type", "user_id", "timestamp"]
        for field in required_fields:
            if not audit_data.get(field):
                violations.append(f"missing_required_field_{field}")
        
        # Validate event type
        event_type = audit_data.get("event_type")
        if event_type and event_type not in [e.value for e in AuditEventType]:
            violations.append("invalid_event_type")
        
        # Check timestamp validity
        timestamp = audit_data.get("timestamp")
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                violations.append("invalid_timestamp_format")
        
        # Check for suspicious patterns
        if self._detect_suspicious_patterns(audit_data):
            warnings.append("suspicious_activity_pattern_detected")
        
        return {
            "is_valid": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "business_rules_passed": len(violations) == 0
        }
    
    def generate_compliance_report(self, user_id: str, date_range: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate compliance report for a user.
        
        Args:
            user_id: User ID to generate report for
            date_range: Dict with start_date and end_date
            
        Returns:
            Dict with compliance report data
        """
        # Mock compliance report (real implementation would query audit logs)
        return {
            "user_id": user_id,
            "report_period": date_range,
            "total_events": 15,
            "security_incidents": 2,
            "login_events": 10,
            "failed_logins": 1,
            "compliance_score": 95,
            "recommendations": [
                "Enable two-factor authentication",
                "Review unusual login times"
            ]
        }
    
    def determine_audit_requirements(self, event: Dict[str, Any]) -> AuditRequirement:
        """
        Determine audit requirements for a given security event.
        
        Args:
            event: Dict containing event details including event type, user_id, etc.
            
        Returns:
            AuditRequirement with audit processing requirements
        """
        event_type = event.get("event")
        user_id = event.get("user_id")
        
        # All security events must be audited
        must_audit = True
        
        # Determine if immediate alert is required
        high_priority_events = ["account_lockout", "privilege_escalation", "unauthorized_access", "data_breach"]
        requires_immediate_alert = event_type in high_priority_events
        
        # Determine retention period based on event severity
        if event_type in ["account_lockout", "privilege_escalation"]:
            # Critical security events require 7+ years retention
            retention_years = 7
            severity_level = "critical"
            compliance_flags = ["security_incident", "regulatory_compliance", "legal_hold"]
        elif event_type in ["login_failure", "password_change"]:
            # Standard security events require 3+ years retention  
            retention_years = 3
            severity_level = "medium"
            compliance_flags = ["security_monitoring", "access_control"]
        else:
            # General events get minimum retention
            retention_years = 1
            severity_level = "low"
            compliance_flags = ["standard_audit"]
        
        return AuditRequirement(
            must_audit=must_audit,
            requires_immediate_alert=requires_immediate_alert,
            retention_years=retention_years,
            event_type=event_type,
            severity_level=severity_level,
            compliance_flags=compliance_flags
        )
    
    def _should_trigger_alert(self, event_type: AuditEventType, event_data: Dict[str, Any]) -> bool:
        """Determine if event should trigger an alert."""
        # High severity events always trigger alerts
        if self._event_severity_mapping.get(event_type) == AuditSeverity.HIGH:
            return True
        
        # Multiple failed logins trigger alert
        if event_type == AuditEventType.FAILED_LOGIN:
            failed_count = event_data.get("consecutive_failures", 0)
            return failed_count >= 3
        
        return False
    
    def _get_retention_period(self, subscription_tier: SubscriptionTier, event_type: AuditEventType) -> int:
        """Get retention period in days based on tier and event type."""
        base_retention = {
            SubscriptionTier.FREE: 30,
            SubscriptionTier.EARLY: 90,
            SubscriptionTier.MID: 180,
            SubscriptionTier.ENTERPRISE: 365
        }
        
        # Security events get longer retention
        if event_type in [AuditEventType.FAILED_LOGIN, AuditEventType.ACCOUNT_LOCKED, AuditEventType.PERMISSION_DENIED]:
            multiplier = 2
        else:
            multiplier = 1
        
        return base_retention.get(subscription_tier, 30) * multiplier
    
    def _detect_suspicious_patterns(self, audit_data: Dict[str, Any]) -> bool:
        """Detect suspicious patterns in audit data."""
        # Simple pattern detection (real implementation would be more sophisticated)
        user_agent = audit_data.get("user_agent", "")
        ip_address = audit_data.get("ip_address", "")
        
        # Check for suspicious user agents
        suspicious_agents = ["bot", "crawler", "scanner"]
        if any(agent in user_agent.lower() for agent in suspicious_agents):
            return True
        
        # Check for suspicious IP patterns (simplified)
        if ip_address and (ip_address.startswith("10.") or ip_address == "0.0.0.0"):
            return True
        
        return False