"""
Audit Business Logic Comprehensive Unit Tests

Tests audit event processing, compliance tracking, and security event logging
for authentication operations for Issue #718.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - critical compliance infrastructure
- Business Goal: Protect $500K+ ARR through regulatory compliance and security auditing
- Value Impact: Ensures legal compliance and provides security incident visibility
- Strategic Impact: Enables compliance certification and security incident response
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

from auth_service.auth_core.audit.audit_business_logic import (
    AuditBusinessLogic,
    AuditEventType,
    AuditSeverity,
    AuditEventResult,
    AuditRequirement
)
from netra_backend.app.schemas.tenant import SubscriptionTier


class AuditBusinessLogicTests(SSotBaseTestCase):
    """Comprehensive unit tests for audit business logic."""

    def setUp(self):
        """Set up test environment with SSOT patterns."""
        super().setUp()
        self.mock_auth_env = SSotMockFactory.create_mock_auth_environment()
        self.audit_logic = AuditBusinessLogic(self.mock_auth_env)

        # Base event data template
        self.base_event_data = {
            "event_type": "user_login",
            "user_id": "test_user_123",
            "subscription_tier": SubscriptionTier.EARLY,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 test browser"
        }

    def test_process_audit_event_user_login(self):
        """Test processing user login audit events."""
        event_data = self.base_event_data.copy()
        event_data["event_type"] = "user_login"

        result = self.audit_logic.process_audit_event(event_data)

        self.assertIsInstance(result, AuditEventResult)
        self.assertEqual(result.event_type, AuditEventType.USER_LOGIN)
        self.assertEqual(result.severity, AuditSeverity.LOW)
        self.assertTrue(result.logged)
        self.assertFalse(result.requires_alert)  # Normal login shouldn't trigger alert
        self.assertIn("access_control", result.compliance_tags)
        self.assertIn("authentication", result.compliance_tags)

    def test_process_audit_event_failed_login(self):
        """Test processing failed login audit events."""
        event_data = self.base_event_data.copy()
        event_data["event_type"] = "failed_login"
        event_data["consecutive_failures"] = 3  # Should trigger alert

        result = self.audit_logic.process_audit_event(event_data)

        self.assertEqual(result.event_type, AuditEventType.FAILED_LOGIN)
        self.assertEqual(result.severity, AuditSeverity.MEDIUM)
        self.assertTrue(result.requires_alert)  # Multiple failures should trigger alert
        self.assertIn("security_incident", result.compliance_tags)

    def test_process_audit_event_account_locked(self):
        """Test processing account lockout audit events."""
        event_data = self.base_event_data.copy()
        event_data["event_type"] = "account_locked"

        result = self.audit_logic.process_audit_event(event_data)

        self.assertEqual(result.event_type, AuditEventType.ACCOUNT_LOCKED)
        self.assertEqual(result.severity, AuditSeverity.HIGH)
        self.assertTrue(result.requires_alert)  # High severity always triggers alert
        self.assertIn("security_incident", result.compliance_tags)
        self.assertIn("account_security", result.compliance_tags)

    def test_process_audit_event_permission_denied(self):
        """Test processing permission denied audit events."""
        event_data = self.base_event_data.copy()
        event_data["event_type"] = "permission_denied"

        result = self.audit_logic.process_audit_event(event_data)

        self.assertEqual(result.event_type, AuditEventType.PERMISSION_DENIED)
        self.assertEqual(result.severity, AuditSeverity.HIGH)
        self.assertTrue(result.requires_alert)
        self.assertIn("access_control", result.compliance_tags)
        self.assertIn("security_incident", result.compliance_tags)

    def test_process_audit_event_oauth_login(self):
        """Test processing OAuth login audit events."""
        event_data = self.base_event_data.copy()
        event_data["event_type"] = "oauth_login"

        result = self.audit_logic.process_audit_event(event_data)

        self.assertEqual(result.event_type, AuditEventType.OAUTH_LOGIN)
        self.assertEqual(result.severity, AuditSeverity.LOW)
        self.assertFalse(result.requires_alert)

    def test_process_audit_event_default_values(self):
        """Test processing audit events with minimal data."""
        minimal_event = {
            "user_id": "test_user"
        }

        result = self.audit_logic.process_audit_event(minimal_event)

        # Should default to user_login event type
        self.assertEqual(result.event_type, AuditEventType.USER_LOGIN)
        self.assertEqual(result.severity, AuditSeverity.LOW)
        self.assertTrue(result.logged)

    def test_retention_period_by_subscription_tier(self):
        """Test retention period calculation based on subscription tier."""
        base_event = self.base_event_data.copy()

        # Test different subscription tiers
        test_cases = [
            (SubscriptionTier.FREE, 60),      # 30 * 2 (security event multiplier)
            (SubscriptionTier.EARLY, 180),    # 90 * 2
            (SubscriptionTier.MID, 360),      # 180 * 2
            (SubscriptionTier.ENTERPRISE, 730) # 365 * 2
        ]

        for tier, expected_days in test_cases:
            base_event["subscription_tier"] = tier
            base_event["event_type"] = "failed_login"  # Security event gets multiplier

            result = self.audit_logic.process_audit_event(base_event)

            self.assertEqual(result.retention_period_days, expected_days)

    def test_retention_period_non_security_events(self):
        """Test retention period for non-security events."""
        event_data = self.base_event_data.copy()
        event_data["event_type"] = "user_logout"  # Non-security event
        event_data["subscription_tier"] = SubscriptionTier.EARLY

        result = self.audit_logic.process_audit_event(event_data)

        # Non-security events don't get multiplier
        self.assertEqual(result.retention_period_days, 90)  # Base retention for EARLY

    def test_event_id_generation(self):
        """Test audit event ID generation."""
        event_data = self.base_event_data.copy()

        result = self.audit_logic.process_audit_event(event_data)

        # Event ID should contain event type and user ID
        self.assertIn("audit_user_login", result.event_id)
        self.assertIn("test_user_123", result.event_id)
        # Should be unique (contains timestamp)
        self.assertTrue(len(result.event_id) > 20)

    def test_validate_audit_business_rules_valid_data(self):
        """Test audit data validation with valid data."""
        valid_audit_data = {
            "event_type": "user_login",
            "user_id": "test_user_123",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        validation = self.audit_logic.validate_audit_business_rules(valid_audit_data)

        self.assertTrue(validation["is_valid"])
        self.assertTrue(validation["business_rules_passed"])
        self.assertEqual(len(validation["violations"]), 0)

    def test_validate_audit_business_rules_missing_fields(self):
        """Test audit data validation with missing required fields."""
        invalid_data = {
            "event_type": "user_login",
            # Missing user_id and timestamp
        }

        validation = self.audit_logic.validate_audit_business_rules(invalid_data)

        self.assertFalse(validation["is_valid"])
        self.assertFalse(validation["business_rules_passed"])
        self.assertIn("missing_required_field_user_id", validation["violations"])
        self.assertIn("missing_required_field_timestamp", validation["violations"])

    def test_validate_audit_business_rules_invalid_event_type(self):
        """Test audit data validation with invalid event type."""
        invalid_data = {
            "event_type": "invalid_event_type",
            "user_id": "test_user",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        validation = self.audit_logic.validate_audit_business_rules(invalid_data)

        self.assertFalse(validation["is_valid"])
        self.assertIn("invalid_event_type", validation["violations"])

    def test_validate_audit_business_rules_invalid_timestamp(self):
        """Test audit data validation with invalid timestamp format."""
        invalid_data = {
            "event_type": "user_login",
            "user_id": "test_user",
            "timestamp": "not_a_timestamp"
        }

        validation = self.audit_logic.validate_audit_business_rules(invalid_data)

        self.assertFalse(validation["is_valid"])
        self.assertIn("invalid_timestamp_format", validation["violations"])

    def test_validate_audit_business_rules_suspicious_patterns(self):
        """Test audit data validation detects suspicious patterns."""
        suspicious_data = {
            "event_type": "user_login",
            "user_id": "test_user",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_agent": "suspicious bot scanner",  # Should trigger warning
            "ip_address": "192.168.1.100"
        }

        validation = self.audit_logic.validate_audit_business_rules(suspicious_data)

        self.assertTrue(validation["is_valid"])  # Still valid, just suspicious
        self.assertIn("suspicious_activity_pattern_detected", validation["warnings"])

    def test_detect_suspicious_patterns_user_agent(self):
        """Test suspicious pattern detection for user agents."""
        test_cases = [
            ("Mozilla/5.0 normal browser", False),
            ("suspicious bot crawler", True),
            ("automated scanner tool", True),
            ("legitimate mobile app", False)
        ]

        for user_agent, should_be_suspicious in test_cases:
            audit_data = {
                "user_agent": user_agent,
                "ip_address": "192.168.1.100"
            }

            result = self.audit_logic._detect_suspicious_patterns(audit_data)
            self.assertEqual(result, should_be_suspicious)

    def test_detect_suspicious_patterns_ip_address(self):
        """Test suspicious pattern detection for IP addresses."""
        test_cases = [
            ("192.168.1.100", False),   # Normal private IP
            ("10.0.0.1", True),         # Private IP starting with 10
            ("0.0.0.0", True),          # Invalid IP
            ("203.0.113.1", False),     # Public IP
        ]

        for ip_address, should_be_suspicious in test_cases:
            audit_data = {
                "user_agent": "normal browser",
                "ip_address": ip_address
            }

            result = self.audit_logic._detect_suspicious_patterns(audit_data)
            self.assertEqual(result, should_be_suspicious)

    def test_generate_compliance_report(self):
        """Test compliance report generation."""
        user_id = "test_user_123"
        date_range = {
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-01-31T23:59:59Z"
        }

        report = self.audit_logic.generate_compliance_report(user_id, date_range)

        # Verify report structure
        self.assertEqual(report["user_id"], user_id)
        self.assertEqual(report["report_period"], date_range)
        self.assertIn("total_events", report)
        self.assertIn("security_incidents", report)
        self.assertIn("login_events", report)
        self.assertIn("failed_logins", report)
        self.assertIn("compliance_score", report)
        self.assertIn("recommendations", report)

        # Verify business logic
        self.assertIsInstance(report["compliance_score"], int)
        self.assertGreaterEqual(report["compliance_score"], 0)
        self.assertLessEqual(report["compliance_score"], 100)

    def test_determine_audit_requirements_critical_events(self):
        """Test audit requirement determination for critical security events."""
        critical_events = [
            "account_lockout",
            "privilege_escalation",
            "unauthorized_access",
            "data_breach"
        ]

        for event_type in critical_events:
            event = {
                "event": event_type,
                "user_id": "test_user",
                "severity": "critical"
            }

            requirement = self.audit_logic.determine_audit_requirements(event)

            self.assertTrue(requirement.must_audit)
            self.assertTrue(requirement.requires_immediate_alert)
            self.assertEqual(requirement.retention_years, 7)
            self.assertEqual(requirement.severity_level, "critical")
            self.assertIn("security_incident", requirement.compliance_flags)
            self.assertIn("regulatory_compliance", requirement.compliance_flags)
            self.assertIn("legal_hold", requirement.compliance_flags)

    def test_determine_audit_requirements_standard_events(self):
        """Test audit requirement determination for standard security events."""
        standard_events = [
            "login_failure",
            "password_change"
        ]

        for event_type in standard_events:
            event = {
                "event": event_type,
                "user_id": "test_user"
            }

            requirement = self.audit_logic.determine_audit_requirements(event)

            self.assertTrue(requirement.must_audit)
            self.assertFalse(requirement.requires_immediate_alert)
            self.assertEqual(requirement.retention_years, 3)
            self.assertEqual(requirement.severity_level, "medium")
            self.assertIn("security_monitoring", requirement.compliance_flags)
            self.assertIn("access_control", requirement.compliance_flags)

    def test_determine_audit_requirements_general_events(self):
        """Test audit requirement determination for general events."""
        event = {
            "event": "general_activity",
            "user_id": "test_user"
        }

        requirement = self.audit_logic.determine_audit_requirements(event)

        self.assertTrue(requirement.must_audit)  # All events must be audited
        self.assertFalse(requirement.requires_immediate_alert)
        self.assertEqual(requirement.retention_years, 1)
        self.assertEqual(requirement.severity_level, "low")
        self.assertIn("standard_audit", requirement.compliance_flags)

    def test_should_trigger_alert_high_severity(self):
        """Test alert triggering for high severity events."""
        high_severity_event = AuditEventType.ACCOUNT_LOCKED
        event_data = {"consecutive_failures": 1}

        should_alert = self.audit_logic._should_trigger_alert(high_severity_event, event_data)

        self.assertTrue(should_alert)

    def test_should_trigger_alert_multiple_failures(self):
        """Test alert triggering for multiple failed logins."""
        event_data_cases = [
            ({"consecutive_failures": 1}, False),  # Below threshold
            ({"consecutive_failures": 2}, False),  # Below threshold
            ({"consecutive_failures": 3}, True),   # At threshold
            ({"consecutive_failures": 5}, True),   # Above threshold
        ]

        for event_data, should_alert in event_data_cases:
            result = self.audit_logic._should_trigger_alert(AuditEventType.FAILED_LOGIN, event_data)
            self.assertEqual(result, should_alert)

    def test_should_trigger_alert_low_severity(self):
        """Test that low severity events don't trigger alerts."""
        low_severity_event = AuditEventType.USER_LOGIN
        event_data = {}

        should_alert = self.audit_logic._should_trigger_alert(low_severity_event, event_data)

        self.assertFalse(should_alert)

    def test_get_retention_period_security_events(self):
        """Test retention period calculation for security events."""
        security_events = [
            AuditEventType.FAILED_LOGIN,
            AuditEventType.ACCOUNT_LOCKED,
            AuditEventType.PERMISSION_DENIED
        ]

        for event_type in security_events:
            retention_days = self.audit_logic._get_retention_period(SubscriptionTier.EARLY, event_type)

            # Security events get 2x multiplier
            expected_days = 90 * 2  # EARLY tier * security multiplier
            self.assertEqual(retention_days, expected_days)

    def test_get_retention_period_normal_events(self):
        """Test retention period calculation for normal events."""
        normal_events = [
            AuditEventType.USER_LOGIN,
            AuditEventType.USER_LOGOUT,
            AuditEventType.OAUTH_LOGIN
        ]

        for event_type in normal_events:
            retention_days = self.audit_logic._get_retention_period(SubscriptionTier.EARLY, event_type)

            # Normal events get 1x multiplier
            expected_days = 90 * 1  # EARLY tier * normal multiplier
            self.assertEqual(retention_days, expected_days)

    def test_business_value_protection_compliance(self):
        """Test that audit system protects business value through compliance."""
        # Simulate high-value enterprise customer audit event
        enterprise_event = {
            "event_type": "permission_denied",
            "user_id": "enterprise_user_456",
            "subscription_tier": SubscriptionTier.ENTERPRISE,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resource_accessed": "sensitive_data",
            "attempted_action": "unauthorized_read"
        }

        result = self.audit_logic.process_audit_event(enterprise_event)

        # High-value customer should get maximum protection
        self.assertEqual(result.severity, AuditSeverity.HIGH)
        self.assertTrue(result.requires_alert)
        self.assertEqual(result.retention_period_days, 730)  # 2 years for enterprise
        self.assertIn("security_incident", result.compliance_tags)

        # Event should be properly logged for compliance
        self.assertTrue(result.logged)
        self.assertIn("enterprise_user_456", result.event_id)


class AuditEventResultTests(SSotBaseTestCase):
    """Test the AuditEventResult dataclass."""

    def test_audit_event_result_creation(self):
        """Test AuditEventResult creation with all fields."""
        result = AuditEventResult(
            event_id="test_event_123",
            event_type=AuditEventType.USER_LOGIN,
            severity=AuditSeverity.LOW,
            logged=True,
            requires_alert=False,
            compliance_tags=["access_control"],
            retention_period_days=90
        )

        self.assertEqual(result.event_id, "test_event_123")
        self.assertEqual(result.event_type, AuditEventType.USER_LOGIN)
        self.assertEqual(result.severity, AuditSeverity.LOW)
        self.assertTrue(result.logged)
        self.assertFalse(result.requires_alert)
        self.assertEqual(result.compliance_tags, ["access_control"])
        self.assertEqual(result.retention_period_days, 90)

    def test_audit_event_result_post_init(self):
        """Test AuditEventResult __post_init__ method."""
        result = AuditEventResult(
            event_id="test_event",
            event_type=AuditEventType.USER_LOGIN,
            severity=AuditSeverity.LOW,
            logged=True
        )

        # compliance_tags should be initialized as empty list
        self.assertEqual(result.compliance_tags, [])


class AuditRequirementTests(SSotBaseTestCase):
    """Test the AuditRequirement dataclass."""

    def test_audit_requirement_creation(self):
        """Test AuditRequirement creation with all fields."""
        requirement = AuditRequirement(
            must_audit=True,
            requires_immediate_alert=True,
            retention_years=7,
            event_type="account_lockout",
            severity_level="critical",
            compliance_flags=["security_incident", "legal_hold"]
        )

        self.assertTrue(requirement.must_audit)
        self.assertTrue(requirement.requires_immediate_alert)
        self.assertEqual(requirement.retention_years, 7)
        self.assertEqual(requirement.event_type, "account_lockout")
        self.assertEqual(requirement.severity_level, "critical")
        self.assertEqual(requirement.compliance_flags, ["security_incident", "legal_hold"])

    def test_audit_requirement_post_init(self):
        """Test AuditRequirement __post_init__ method."""
        requirement = AuditRequirement(
            must_audit=True,
            requires_immediate_alert=False,
            retention_years=1,
            event_type="general_event",
            severity_level="low"
        )

        # compliance_flags should be initialized as empty list
        self.assertEqual(requirement.compliance_flags, [])


class AuditEventTypeTests(SSotBaseTestCase):
    """Test the AuditEventType enum."""

    def test_audit_event_type_values(self):
        """Test that AuditEventType enum has expected values."""
        expected_events = [
            ("USER_LOGIN", "user_login"),
            ("USER_LOGOUT", "user_logout"),
            ("USER_REGISTRATION", "user_registration"),
            ("PASSWORD_CHANGE", "password_change"),
            ("FAILED_LOGIN", "failed_login"),
            ("ACCOUNT_LOCKED", "account_locked"),
            ("OAUTH_LOGIN", "oauth_login"),
            ("PERMISSION_DENIED", "permission_denied"),
            ("SESSION_CREATED", "session_created"),
            ("SESSION_TERMINATED", "session_terminated"),
        ]

        for enum_name, enum_value in expected_events:
            event_type = getattr(AuditEventType, enum_name)
            self.assertEqual(event_type.value, enum_value)


class AuditSeverityTests(SSotBaseTestCase):
    """Test the AuditSeverity enum."""

    def test_audit_severity_values(self):
        """Test that AuditSeverity enum has expected values."""
        expected_severities = [
            ("LOW", "low"),
            ("MEDIUM", "medium"),
            ("HIGH", "high"),
            ("CRITICAL", "critical"),
        ]

        for enum_name, enum_value in expected_severities:
            severity = getattr(AuditSeverity, enum_name)
            self.assertEqual(severity.value, enum_value)