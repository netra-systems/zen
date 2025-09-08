"""
Auth Business Logic Validation Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Correct authentication business logic across user tiers
- Value Impact: Ensures auth system properly enforces business rules
- Strategic Impact: Protects platform revenue and user experience integrity

These tests validate:
1. User registration business rules and validation
2. Login attempt limits and security policies
3. Subscription tier access control
4. Account lifecycle management
5. Business rule enforcement across user types
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch

from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.models.auth_models import LoginRequest, LoginResponse
from auth_service.auth_core.auth_environment import AuthEnvironment
from shared.isolated_environment import get_env
from netra_backend.app.schemas.tenant import SubscriptionTier


class TestAuthBusinessLogicValidation:
    """Comprehensive auth business logic validation tests."""

    @pytest.fixture
    def auth_env(self):
        # Follow SSOT pattern: AuthEnvironment() handles env internally
        auth_env = AuthEnvironment()
        return auth_env

    @pytest.fixture 
    def auth_service(self, auth_env):
        return AuthService()

    @pytest.mark.unit
    def test_user_registration_business_rules(self, auth_service):
        """Test user registration follows business rules."""
        valid_registration = {
            "email": "new.user@company.com",
            "password": "SecurePass123!",
            "name": "New User",
            "subscription_tier": SubscriptionTier.FREE
        }
        
        result = user_business_logic.validate_registration(valid_registration)
        
        assert result.is_valid
        assert result.assigned_tier == SubscriptionTier.FREE
        assert result.trial_days == 14  # Free users get trial
        
        # Test business email validation
        business_registration = valid_registration.copy()
        business_registration["email"] = "user@enterprise.com"
        
        biz_result = user_business_logic.validate_registration(business_registration)
        
        assert biz_result.is_valid
        # Business emails might get upgraded tier
        assert biz_result.suggested_tier in [SubscriptionTier.EARLY, SubscriptionTier.ENTERPRISE]

    @pytest.mark.unit
    def test_subscription_tier_access_control(self, subscription_validator):
        """Test subscription tiers enforce correct access control."""
        tiers_and_limits = [
            (SubscriptionTier.FREE, {"api_calls_per_month": 1000, "agents": 1}),
            (SubscriptionTier.EARLY, {"api_calls_per_month": 10000, "agents": 3}),
            (SubscriptionTier.MID, {"api_calls_per_month": 50000, "agents": 5}),
            (SubscriptionTier.ENTERPRISE, {"api_calls_per_month": None, "agents": None})
        ]
        
        for tier, expected_limits in tiers_and_limits:
            limits = subscription_validator.get_tier_limits(tier)
            
            for limit_name, expected_value in expected_limits.items():
                assert limits[limit_name] == expected_value
                
            # Test access validation
            access_result = subscription_validator.validate_feature_access(
                tier, "advanced_analytics"
            )
            
            if tier in [SubscriptionTier.MID, SubscriptionTier.ENTERPRISE]:
                assert access_result.has_access
            else:
                assert not access_result.has_access
                assert "upgrade" in access_result.upgrade_message.lower()

    @pytest.mark.unit
    def test_login_attempt_business_logic(self, user_business_logic):
        """Test login attempt limits and business logic."""
        user_context = {
            "user_id": "test-user",
            "email": "test@example.com",
            "failed_attempts": 0,
            "last_attempt": datetime.now(timezone.utc)
        }
        
        # First few attempts should be allowed
        for attempt in range(3):
            result = user_business_logic.validate_login_attempt(user_context)
            assert result.allowed
            user_context["failed_attempts"] = attempt + 1
        
        # After threshold, should start rate limiting
        user_context["failed_attempts"] = 5
        result = user_business_logic.validate_login_attempt(user_context)
        
        assert not result.allowed
        assert result.lockout_duration > 0
        assert "try again" in result.message.lower()

    @pytest.mark.unit
    def test_account_lifecycle_management(self, user_business_logic):
        """Test account lifecycle business rules."""
        # Test new account activation
        new_account = {
            "created_at": datetime.now(timezone.utc),
            "email_verified": False,
            "status": "pending_verification"
        }
        
        lifecycle_result = user_business_logic.process_account_lifecycle(new_account)
        
        assert lifecycle_result.requires_email_verification
        assert lifecycle_result.grace_period_days == 7
        
        # Test expired trial account
        expired_trial = {
            "created_at": datetime.now(timezone.utc) - timedelta(days=15),
            "subscription_tier": SubscriptionTier.FREE,
            "trial_expired": True
        }
        
        expired_result = user_business_logic.process_account_lifecycle(expired_trial)
        
        assert expired_result.requires_upgrade
        assert expired_result.limited_access
        assert "upgrade" in expired_result.message.lower()

    @pytest.mark.unit
    def test_business_rule_compliance_validation(self, user_business_logic, subscription_validator):
        """Test business rule compliance across different scenarios."""
        # Test free tier usage limits
        free_user_usage = {
            "subscription_tier": SubscriptionTier.FREE,
            "current_month_api_calls": 950,
            "current_agents": 1
        }
        
        compliance_result = subscription_validator.validate_usage_compliance(free_user_usage)
        
        assert compliance_result.within_limits
        assert compliance_result.usage_percentage < 100
        
        # Test over-limit usage
        over_limit_usage = free_user_usage.copy()
        over_limit_usage["current_month_api_calls"] = 1100
        
        over_limit_result = subscription_validator.validate_usage_compliance(over_limit_usage)
        
        assert not over_limit_result.within_limits
        assert over_limit_result.requires_upgrade
        assert over_limit_result.overage_amount > 0


class TestAuthCrossServiceValidation:
    """Test 7: Cross-service validation business logic."""

    @pytest.fixture
    def auth_env(self):
        # Follow SSOT pattern: AuthEnvironment() handles env internally
        return AuthEnvironment()

    @pytest.mark.unit
    def test_cross_service_token_validation_business_logic(self, auth_env):
        """Test cross-service token validation business rules."""
        from auth_service.auth_core.security.cross_service_validator import CrossServiceValidator
        
        validator = CrossServiceValidator(auth_env)
        
        # Test valid cross-service request
        service_request = {
            "requesting_service": "backend",
            "target_resource": "user_data",
            "user_context": {"user_id": "user-123", "tier": "enterprise"},
            "operation": "read"
        }
        
        validation_result = validator.validate_cross_service_request(service_request)
        
        assert validation_result.is_authorized
        assert validation_result.allowed_operations == ["read"]
        
        # Test unauthorized cross-service request
        unauthorized_request = service_request.copy()
        unauthorized_request["operation"] = "delete"
        unauthorized_request["user_context"]["tier"] = "free"
        
        unauthorized_result = validator.validate_cross_service_request(unauthorized_request)
        
        assert not unauthorized_result.is_authorized
        assert "insufficient privileges" in unauthorized_result.denial_reason.lower()


class TestAuthSecurityPolicyValidation:
    """Test 8: Security policy validation business logic."""

    @pytest.fixture
    def auth_env(self):
        # Follow SSOT pattern: AuthEnvironment() handles env internally
        return AuthEnvironment()

    @pytest.mark.unit
    def test_password_policy_business_rules(self, auth_env):
        """Test password policy business rules."""
        from auth_service.auth_core.security.password_policy_validator import PasswordPolicyValidator
        
        validator = PasswordPolicyValidator(auth_env)
        
        # Test strong password
        strong_password = "MySecureP@ssw0rd123!"
        result = validator.validate_password_policy(strong_password)
        
        assert result.meets_policy
        assert result.strength_score >= 80
        
        # Test weak password
        weak_password = "password123"
        weak_result = validator.validate_password_policy(weak_password)
        
        assert not weak_result.meets_policy
        assert "special characters" in weak_result.requirements_missing[0].lower()

    @pytest.mark.unit  
    def test_session_security_policy(self, auth_env):
        """Test session security policy enforcement."""
        from auth_service.auth_core.security.session_policy_validator import SessionPolicyValidator
        
        validator = SessionPolicyValidator(auth_env)
        
        # Test concurrent session limits
        session_request = {
            "user_id": "user-123",
            "current_sessions": 2,
            "subscription_tier": SubscriptionTier.FREE,
            "device_info": {"type": "web", "ip": "192.168.1.1"}
        }
        
        result = validator.validate_session_policy(session_request)
        
        # Free users should have session limits
        assert result.max_concurrent_sessions == 3
        if session_request["current_sessions"] >= result.max_concurrent_sessions:
            assert not result.can_create_new_session


class TestAuthIntegrationBusinessLogic:
    """Test 9: OAuth integration business logic."""

    @pytest.fixture
    def auth_env(self):
        # Follow SSOT pattern: AuthEnvironment() handles env internally
        return AuthEnvironment()

    @pytest.mark.unit
    def test_oauth_integration_business_rules(self, auth_env):
        """Test OAuth integration follows business rules."""
        from auth_service.auth_core.oauth.oauth_business_logic import OAuthBusinessLogic
        
        oauth_logic = OAuthBusinessLogic(auth_env)
        
        # Test first-time OAuth user
        oauth_user_data = {
            "provider": "google",
            "provider_user_id": "google-123",
            "email": "user@gmail.com",
            "verified_email": True,
            "name": "Test User"
        }
        
        result = oauth_logic.process_oauth_user(oauth_user_data)
        
        assert result.should_create_account
        assert result.suggested_tier == SubscriptionTier.FREE
        assert result.email_verification_required is False  # OAuth email already verified
        
        # Test existing user OAuth linking
        existing_user_oauth = oauth_user_data.copy()
        existing_user_oauth["existing_user_id"] = "user-456"
        
        link_result = oauth_logic.process_oauth_user(existing_user_oauth)
        
        assert not link_result.should_create_account
        assert link_result.should_link_accounts


class TestAuthAuditBusinessLogic:
    """Test 10: Audit and compliance business logic."""

    @pytest.fixture
    def auth_env(self):
        # Follow SSOT pattern: AuthEnvironment() handles env internally
        return AuthEnvironment()

    @pytest.mark.unit
    def test_audit_logging_business_rules(self, auth_env):
        """Test audit logging follows business compliance rules."""
        from auth_service.auth_core.audit.audit_business_logic import AuditBusinessLogic
        
        audit_logic = AuditBusinessLogic(auth_env)
        
        # Test security event audit requirement
        security_events = [
            {"event": "login_failure", "user_id": "user-123", "attempts": 5},
            {"event": "password_change", "user_id": "user-456"},
            {"event": "account_lockout", "user_id": "user-789"},
            {"event": "privilege_escalation", "user_id": "admin-123"}
        ]
        
        for event in security_events:
            audit_requirement = audit_logic.determine_audit_requirements(event)
            
            assert audit_requirement.must_audit
            if event["event"] in ["account_lockout", "privilege_escalation"]:
                assert audit_requirement.requires_immediate_alert
                assert audit_requirement.retention_years >= 7
            else:
                assert audit_requirement.retention_years >= 3

    @pytest.mark.unit
    def test_compliance_reporting_business_logic(self, auth_env):
        """Test compliance reporting business logic."""
        from auth_service.auth_core.compliance.compliance_business_logic import ComplianceBusinessLogic
        
        compliance_logic = ComplianceBusinessLogic(auth_env)
        
        # Test data retention policy
        user_data_age_scenarios = [
            {"user_id": "active-user", "last_login": 30, "subscription": "enterprise"},
            {"user_id": "inactive-user", "last_login": 400, "subscription": "free"},
            {"user_id": "deleted-user", "last_login": 800, "subscription": "free", "deleted": True}
        ]
        
        for scenario in user_data_age_scenarios:
            retention_policy = compliance_logic.determine_data_retention_policy(scenario)
            
            if scenario.get("deleted"):
                assert retention_policy.should_purge_data
                assert retention_policy.purge_delay_days <= 30
            elif scenario["last_login"] > 365 and scenario["subscription"] == "free":
                assert retention_policy.should_archive_data
            else:
                assert retention_policy.should_retain_data
                assert retention_policy.retention_years >= 1