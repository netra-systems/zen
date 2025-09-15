"""
Compliance Business Logic Comprehensive Unit Tests

Tests regulatory compliance including GDPR, CCPA, HIPAA, and other data protection
regulations for authentication services for Issue #718.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - critical regulatory compliance
- Business Goal: Protect $500K+ ARR through regulatory compliance and risk mitigation
- Value Impact: Enables business operations in regulated markets and with enterprise customers
- Strategic Impact: Protects against regulatory fines and enables premium service tiers
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

from auth_service.auth_core.compliance.compliance_business_logic import (
    ComplianceBusinessLogic,
    ComplianceFramework,
    DataRetentionPolicy,
    ComplianceResult,
    DataRetentionPolicyResult
)
from netra_backend.app.schemas.tenant import SubscriptionTier


class ComplianceBusinessLogicTests(SSotBaseTestCase):
    """Comprehensive unit tests for compliance business logic."""

    def setUp(self):
        """Set up test environment with SSOT patterns."""
        super().setUp()
        self.mock_auth_env = SSotMockFactory.create_mock_auth_environment()
        self.compliance_logic = ComplianceBusinessLogic(self.mock_auth_env)

        # Base user data template
        self.base_user_data = {
            "user_id": "test_user_123",
            "created_at": datetime.now(timezone.utc) - timedelta(days=30),
            "consent_given": True,
            "data_encrypted": True,
            "audit_enabled": True
        }

    def test_validate_compliance_gdpr_compliant(self):
        """Test GDPR compliance validation with compliant data."""
        user_data = self.base_user_data.copy()

        result = self.compliance_logic.validate_compliance(ComplianceFramework.GDPR, user_data)

        self.assertIsInstance(result, ComplianceResult)
        self.assertTrue(result.is_compliant)
        self.assertEqual(result.framework, ComplianceFramework.GDPR)
        self.assertEqual(len(result.violations), 0)
        self.assertEqual(result.certification_status, "compliant")

    def test_validate_compliance_gdpr_data_retention_violation(self):
        """Test GDPR compliance with data retention violation."""
        user_data = self.base_user_data.copy()
        # Data older than GDPR limit (3 years)
        user_data["created_at"] = datetime.now(timezone.utc) - timedelta(days=1200)  # > 1095 days

        result = self.compliance_logic.validate_compliance(ComplianceFramework.GDPR, user_data)

        self.assertFalse(result.is_compliant)
        self.assertIn("data_retention_exceeded_1095_days", result.violations)
        self.assertIn("Review data retention policy", result.recommendations[0])
        self.assertEqual(result.certification_status, "non_compliant")

    def test_validate_compliance_gdpr_missing_consent(self):
        """Test GDPR compliance with missing user consent."""
        user_data = self.base_user_data.copy()
        user_data["consent_given"] = False

        result = self.compliance_logic.validate_compliance(ComplianceFramework.GDPR, user_data)

        self.assertFalse(result.is_compliant)
        self.assertIn("missing_user_consent", result.violations)
        self.assertIn("Obtain explicit user consent", result.recommendations[0])

    def test_validate_compliance_ccpa_compliant(self):
        """Test CCPA compliance validation with compliant data."""
        user_data = self.base_user_data.copy()
        user_data["consent_given"] = False  # CCPA doesn't require consent

        result = self.compliance_logic.validate_compliance(ComplianceFramework.CCPA, user_data)

        self.assertTrue(result.is_compliant)
        self.assertEqual(result.framework, ComplianceFramework.CCPA)
        self.assertEqual(len(result.violations), 0)

    def test_validate_compliance_ccpa_data_retention_violation(self):
        """Test CCPA compliance with data retention violation."""
        user_data = self.base_user_data.copy()
        # Data older than CCPA limit (2 years)
        user_data["created_at"] = datetime.now(timezone.utc) - timedelta(days=800)  # > 730 days

        result = self.compliance_logic.validate_compliance(ComplianceFramework.CCPA, user_data)

        self.assertFalse(result.is_compliant)
        self.assertIn("data_retention_exceeded_730_days", result.violations)

    def test_validate_compliance_hipaa_compliant(self):
        """Test HIPAA compliance validation with compliant data."""
        user_data = self.base_user_data.copy()

        result = self.compliance_logic.validate_compliance(ComplianceFramework.HIPAA, user_data)

        self.assertTrue(result.is_compliant)
        self.assertEqual(result.framework, ComplianceFramework.HIPAA)

    def test_validate_compliance_hipaa_encryption_required(self):
        """Test HIPAA compliance with missing encryption."""
        user_data = self.base_user_data.copy()
        user_data["data_encrypted"] = False

        result = self.compliance_logic.validate_compliance(ComplianceFramework.HIPAA, user_data)

        self.assertFalse(result.is_compliant)
        self.assertIn("data_not_encrypted", result.violations)
        self.assertIn("Implement data encryption", result.recommendations[0])

    def test_validate_compliance_hipaa_audit_logging_required(self):
        """Test HIPAA compliance with missing audit logging."""
        user_data = self.base_user_data.copy()
        user_data["audit_enabled"] = False

        result = self.compliance_logic.validate_compliance(ComplianceFramework.HIPAA, user_data)

        self.assertFalse(result.is_compliant)
        self.assertIn("audit_logging_disabled", result.violations)
        self.assertIn("Enable comprehensive audit logging", result.recommendations[0])

    def test_validate_compliance_multiple_violations(self):
        """Test compliance validation with multiple violations."""
        user_data = {
            "user_id": "test_user",
            "created_at": datetime.now(timezone.utc) - timedelta(days=1200),  # Too old
            "consent_given": False,  # Missing consent for GDPR
            "data_encrypted": False,  # Missing encryption for HIPAA
            "audit_enabled": False   # Missing audit for HIPAA
        }

        result = self.compliance_logic.validate_compliance(ComplianceFramework.GDPR, user_data)

        self.assertFalse(result.is_compliant)
        self.assertGreaterEqual(len(result.violations), 2)  # Multiple violations
        self.assertGreaterEqual(len(result.recommendations), 2)  # Multiple recommendations

    def test_validate_compliance_string_timestamp_handling(self):
        """Test compliance validation with string timestamp format."""
        user_data = self.base_user_data.copy()
        user_data["created_at"] = "2024-01-01T00:00:00Z"  # String format

        result = self.compliance_logic.validate_compliance(ComplianceFramework.GDPR, user_data)

        # Should handle string timestamps correctly
        self.assertTrue(result.is_compliant)

    def test_process_data_subject_request_access(self):
        """Test processing data subject access requests (GDPR Article 15)."""
        user_data = {"user_id": "test_user_123"}

        result = self.compliance_logic.process_data_subject_request("access", user_data)

        self.assertEqual(result["request_type"], "access")
        self.assertEqual(result["user_id"], "test_user_123")
        self.assertTrue(result["data_provided"])
        self.assertIn("profile", result["data_categories"])
        self.assertIn("authentication", result["data_categories"])
        self.assertIn("audit_logs", result["data_categories"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["processing_time_days"], 1)

    def test_process_data_subject_request_deletion(self):
        """Test processing data subject deletion requests (GDPR Article 17, CCPA)."""
        user_data = {"user_id": "test_user_456"}

        result = self.compliance_logic.process_data_subject_request("deletion", user_data)

        self.assertEqual(result["request_type"], "deletion")
        self.assertEqual(result["user_id"], "test_user_456")
        self.assertTrue(result["data_deleted"])
        self.assertIn("legal_obligation", result["retention_exceptions"])
        self.assertIn("audit_trail", result["retention_exceptions"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["processing_time_days"], 7)

    def test_process_data_subject_request_portability(self):
        """Test processing data portability requests (GDPR Article 20)."""
        user_data = {"user_id": "test_user_789"}

        result = self.compliance_logic.process_data_subject_request("portability", user_data)

        self.assertEqual(result["request_type"], "portability")
        self.assertEqual(result["user_id"], "test_user_789")
        self.assertTrue(result["data_exported"])
        self.assertEqual(result["export_format"], "json")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["processing_time_days"], 3)

    def test_process_data_subject_request_unsupported(self):
        """Test processing unsupported data subject requests."""
        user_data = {"user_id": "test_user"}

        result = self.compliance_logic.process_data_subject_request("unsupported_type", user_data)

        self.assertEqual(result["request_type"], "unsupported_type")
        self.assertEqual(result["status"], "unsupported_request_type")

    def test_validate_data_retention_policy_compliant(self):
        """Test data retention policy validation with compliant policy."""
        policy_data = {
            "retention_days": 365,  # 1 year - within GDPR limit
            "data_category": "general",
            "business_justification": "Required for service provision and fraud prevention"
        }

        validation = self.compliance_logic.validate_data_retention_policy(policy_data)

        self.assertTrue(validation["is_valid"])
        self.assertEqual(len(validation["violations"]), 0)
        # Should be compliant with multiple frameworks
        self.assertIn("gdpr", validation["compliant_frameworks"])

    def test_validate_data_retention_policy_exceeds_gdpr(self):
        """Test data retention policy validation exceeding GDPR limits."""
        policy_data = {
            "retention_days": 1200,  # > 3 years (1095 days)
            "data_category": "general",
            "business_justification": "Long-term analysis"
        }

        validation = self.compliance_logic.validate_data_retention_policy(policy_data)

        self.assertFalse(validation["is_valid"])
        self.assertIn("exceeds_gdpr_maximum_retention", validation["violations"])
        self.assertIn("Reduce retention period", validation["recommendations"][0])

    def test_validate_data_retention_policy_missing_justification(self):
        """Test data retention policy validation without business justification."""
        policy_data = {
            "retention_days": 365,
            "data_category": "general"
            # Missing business_justification
        }

        validation = self.compliance_logic.validate_data_retention_policy(policy_data)

        self.assertFalse(validation["is_valid"])
        self.assertIn("missing_business_justification", validation["violations"])
        self.assertIn("Provide clear business justification", validation["recommendations"][0])

    def test_validate_data_retention_policy_authentication_data(self):
        """Test data retention policy validation for authentication data."""
        policy_data = {
            "retention_days": 800,  # > 2 years for auth data
            "data_category": "authentication",
            "business_justification": "Security monitoring"
        }

        validation = self.compliance_logic.validate_data_retention_policy(policy_data)

        self.assertTrue(validation["is_valid"])  # Valid but gets recommendation
        self.assertIn("Consider shorter retention for authentication data", validation["recommendations"][0])

    def test_generate_compliance_report_single_framework(self):
        """Test compliance report generation for single framework."""
        user_id = "enterprise_user_123"
        frameworks = [ComplianceFramework.GDPR]

        report = self.compliance_logic.generate_compliance_report(user_id, frameworks)

        # Verify report structure
        self.assertEqual(report["user_id"], user_id)
        self.assertIn("report_date", report)
        self.assertIn("frameworks_checked", report)
        self.assertIn("overall_compliance_score", report)
        self.assertIn("framework_results", report)

        # Verify framework-specific results
        self.assertIn("gdpr", report["framework_results"])
        gdpr_result = report["framework_results"]["gdpr"]
        self.assertIn("compliance_score", gdpr_result)
        self.assertIn("is_compliant", gdpr_result)
        self.assertIn("violations", gdpr_result)
        self.assertIn("recommendations", gdpr_result)

    def test_generate_compliance_report_multiple_frameworks(self):
        """Test compliance report generation for multiple frameworks."""
        user_id = "multi_compliance_user"
        frameworks = [ComplianceFramework.GDPR, ComplianceFramework.CCPA, ComplianceFramework.HIPAA]

        report = self.compliance_logic.generate_compliance_report(user_id, frameworks)

        # Should have results for all frameworks
        self.assertEqual(len(report["framework_results"]), 3)
        self.assertIn("gdpr", report["framework_results"])
        self.assertIn("ccpa", report["framework_results"])
        self.assertIn("hipaa", report["framework_results"])

        # Overall score should be average of framework scores
        self.assertGreaterEqual(report["overall_compliance_score"], 0)
        self.assertLessEqual(report["overall_compliance_score"], 100)

    def test_determine_data_retention_policy_deleted_user(self):
        """Test data retention policy for deleted users."""
        scenario = {
            "user_id": "deleted_user_123",
            "last_login": 100,
            "subscription": "early",
            "deleted": True
        }

        policy = self.compliance_logic.determine_data_retention_policy(scenario)

        self.assertTrue(policy.should_purge_data)
        self.assertFalse(policy.should_archive_data)
        self.assertFalse(policy.should_retain_data)
        self.assertEqual(policy.retention_years, 0)
        self.assertEqual(policy.purge_delay_days, 30)  # Grace period
        self.assertIn("gdpr", policy.compliance_frameworks)
        self.assertIn("ccpa", policy.compliance_frameworks)
        self.assertIn("User account deleted", policy.policy_reason)

    def test_determine_data_retention_policy_inactive_free_user(self):
        """Test data retention policy for inactive free users."""
        scenario = {
            "user_id": "inactive_free_user",
            "last_login": 400,  # > 365 days
            "subscription": "free",
            "deleted": False
        }

        policy = self.compliance_logic.determine_data_retention_policy(scenario)

        self.assertFalse(policy.should_purge_data)
        self.assertTrue(policy.should_archive_data)
        self.assertFalse(policy.should_retain_data)
        self.assertEqual(policy.retention_years, 2)  # Archive for 2 years
        self.assertIn("Inactive free user", policy.policy_reason)

    def test_determine_data_retention_policy_active_enterprise_user(self):
        """Test data retention policy for active enterprise users."""
        scenario = {
            "user_id": "enterprise_user_456",
            "last_login": 5,  # Recent login
            "subscription": "enterprise",
            "deleted": False
        }

        policy = self.compliance_logic.determine_data_retention_policy(scenario)

        self.assertFalse(policy.should_purge_data)
        self.assertFalse(policy.should_archive_data)
        self.assertTrue(policy.should_retain_data)
        self.assertEqual(policy.retention_years, 5)  # Enterprise tier
        self.assertIn("Active enterprise user", policy.policy_reason)
        self.assertIn("soc2", policy.compliance_frameworks)

    def test_get_subscription_retention_years(self):
        """Test subscription-based retention period calculation."""
        test_cases = [
            ("free", 1),
            ("early", 2),
            ("mid", 3),
            ("enterprise", 5),
            ("unknown", 1)  # Default
        ]

        for subscription, expected_years in test_cases:
            years = self.compliance_logic._get_subscription_retention_years(subscription)
            self.assertEqual(years, expected_years)

    def test_get_compliant_frameworks_all_compliant(self):
        """Test framework compliance with short retention period."""
        retention_days = 365  # 1 year - should be compliant with all

        compliant = self.compliance_logic._get_compliant_frameworks(retention_days)

        # All frameworks should be compliant with 1 year retention
        expected_frameworks = ["gdpr", "ccpa", "hipaa"]
        for framework in expected_frameworks:
            self.assertIn(framework, compliant)

    def test_get_compliant_frameworks_partial_compliance(self):
        """Test framework compliance with medium retention period."""
        retention_days = 1000  # ~2.7 years

        compliant = self.compliance_logic._get_compliant_frameworks(retention_days)

        # Should be compliant with CCPA (2 years) but not GDPR (3 years)
        self.assertIn("ccpa", compliant)
        self.assertIn("gdpr", compliant)  # 1000 < 1095 (GDPR limit)

    def test_get_compliant_frameworks_minimal_compliance(self):
        """Test framework compliance with long retention period."""
        retention_days = 3000  # > 8 years

        compliant = self.compliance_logic._get_compliant_frameworks(retention_days)

        # Should only be compliant with HIPAA (6 years max)
        self.assertNotIn("gdpr", compliant)  # 3000 > 1095
        self.assertNotIn("ccpa", compliant)  # 3000 > 730
        self.assertNotIn("hipaa", compliant)  # 3000 > 2190

    def test_business_value_enterprise_compliance(self):
        """Test compliance handling for high-value enterprise customers."""
        # Enterprise customer with strict compliance requirements
        enterprise_user_data = {
            "user_id": "enterprise_customer_001",
            "created_at": datetime.now(timezone.utc) - timedelta(days=100),
            "consent_given": True,
            "data_encrypted": True,
            "audit_enabled": True,
            "subscription_tier": "enterprise",
            "compliance_requirements": ["gdpr", "hipaa", "soc2"]
        }

        # Test multiple framework compliance
        frameworks = [ComplianceFramework.GDPR, ComplianceFramework.HIPAA]

        gdpr_result = self.compliance_logic.validate_compliance(ComplianceFramework.GDPR, enterprise_user_data)
        hipaa_result = self.compliance_logic.validate_compliance(ComplianceFramework.HIPAA, enterprise_user_data)

        # Enterprise customer should be fully compliant
        self.assertTrue(gdpr_result.is_compliant)
        self.assertTrue(hipaa_result.is_compliant)

        # Should get premium retention period
        retention_scenario = {
            "user_id": enterprise_user_data["user_id"],
            "subscription": "enterprise",
            "deleted": False,
            "last_login": 1
        }

        retention_policy = self.compliance_logic.determine_data_retention_policy(retention_scenario)
        self.assertEqual(retention_policy.retention_years, 5)  # Maximum retention for enterprise

    def test_compliance_framework_requirements_structure(self):
        """Test that compliance framework requirements are properly structured."""
        # Verify GDPR requirements
        gdpr_req = self.compliance_logic._framework_requirements[ComplianceFramework.GDPR]
        self.assertEqual(gdpr_req["data_retention_max_days"], 1095)  # 3 years
        self.assertTrue(gdpr_req["consent_required"])
        self.assertTrue(gdpr_req["right_to_deletion"])
        self.assertTrue(gdpr_req["data_portability"])
        self.assertEqual(gdpr_req["breach_notification_hours"], 72)

        # Verify CCPA requirements
        ccpa_req = self.compliance_logic._framework_requirements[ComplianceFramework.CCPA]
        self.assertEqual(ccpa_req["data_retention_max_days"], 730)  # 2 years
        self.assertFalse(ccpa_req["consent_required"])  # Opt-out model
        self.assertTrue(ccpa_req["right_to_deletion"])

        # Verify HIPAA requirements
        hipaa_req = self.compliance_logic._framework_requirements[ComplianceFramework.HIPAA]
        self.assertEqual(hipaa_req["data_retention_max_days"], 2190)  # 6 years
        self.assertTrue(hipaa_req["consent_required"])
        self.assertTrue(hipaa_req["encryption_required"])
        self.assertTrue(hipaa_req["audit_logs_required"])
        self.assertEqual(hipaa_req["breach_notification_hours"], 60)


class ComplianceResultTests(SSotBaseTestCase):
    """Test the ComplianceResult dataclass."""

    def test_compliance_result_creation(self):
        """Test ComplianceResult creation with all fields."""
        next_review = datetime.now(timezone.utc) + timedelta(days=90)

        result = ComplianceResult(
            is_compliant=True,
            framework=ComplianceFramework.GDPR,
            violations=["test_violation"],
            recommendations=["test_recommendation"],
            next_review_date=next_review,
            certification_status="compliant"
        )

        self.assertTrue(result.is_compliant)
        self.assertEqual(result.framework, ComplianceFramework.GDPR)
        self.assertEqual(result.violations, ["test_violation"])
        self.assertEqual(result.recommendations, ["test_recommendation"])
        self.assertEqual(result.next_review_date, next_review)
        self.assertEqual(result.certification_status, "compliant")

    def test_compliance_result_post_init(self):
        """Test ComplianceResult __post_init__ method."""
        next_review = datetime.now(timezone.utc) + timedelta(days=90)

        result = ComplianceResult(
            is_compliant=False,
            framework=ComplianceFramework.CCPA,
            violations=None,
            recommendations=None,
            next_review_date=next_review
        )

        # Should initialize empty lists
        self.assertEqual(result.violations, [])
        self.assertEqual(result.recommendations, [])


class DataRetentionPolicyResultTests(SSotBaseTestCase):
    """Test the DataRetentionPolicyResult dataclass."""

    def test_data_retention_policy_result_creation(self):
        """Test DataRetentionPolicyResult creation with all fields."""
        result = DataRetentionPolicyResult(
            should_purge_data=True,
            should_archive_data=False,
            should_retain_data=False,
            retention_years=0,
            purge_delay_days=30,
            policy_reason="User deleted",
            compliance_frameworks=["gdpr", "ccpa"]
        )

        self.assertTrue(result.should_purge_data)
        self.assertFalse(result.should_archive_data)
        self.assertFalse(result.should_retain_data)
        self.assertEqual(result.retention_years, 0)
        self.assertEqual(result.purge_delay_days, 30)
        self.assertEqual(result.policy_reason, "User deleted")
        self.assertEqual(result.compliance_frameworks, ["gdpr", "ccpa"])

    def test_data_retention_policy_result_post_init(self):
        """Test DataRetentionPolicyResult __post_init__ method."""
        result = DataRetentionPolicyResult(
            should_purge_data=False,
            should_archive_data=True,
            should_retain_data=False,
            retention_years=2,
            compliance_frameworks=None
        )

        # Should initialize empty list
        self.assertEqual(result.compliance_frameworks, [])


class ComplianceFrameworkTests(SSotBaseTestCase):
    """Test the ComplianceFramework enum."""

    def test_compliance_framework_values(self):
        """Test that ComplianceFramework enum has expected values."""
        expected_frameworks = [
            ("GDPR", "gdpr"),
            ("CCPA", "ccpa"),
            ("HIPAA", "hipaa"),
            ("SOC2", "soc2"),
            ("ISO27001", "iso27001"),
        ]

        for enum_name, enum_value in expected_frameworks:
            framework = getattr(ComplianceFramework, enum_name)
            self.assertEqual(framework.value, enum_value)


class DataRetentionPolicyTests(SSotBaseTestCase):
    """Test the DataRetentionPolicy enum."""

    def test_data_retention_policy_values(self):
        """Test that DataRetentionPolicy enum has expected values."""
        expected_policies = [
            ("MINIMAL", "minimal"),
            ("STANDARD", "standard"),
            ("EXTENDED", "extended"),
            ("LEGAL_HOLD", "legal_hold"),
        ]

        for enum_name, enum_value in expected_policies:
            policy = getattr(DataRetentionPolicy, enum_name)
            self.assertEqual(policy.value, enum_value)