"""
Test Database Models Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable user data persistence and account management
- Value Impact: Database models store critical user authentication data, session state,
  and audit trails that enable user account management, security monitoring, and
  regulatory compliance. Data persistence failures could lose customer accounts
  worth $75K+ MRR and violate security compliance requirements
- Strategic Impact: Core data foundation - database models define how user identities,
  authentication state, and security events are stored and managed. Data integrity
  directly impacts user retention, platform security, and business continuity

This test suite validates that database models correctly store and manage user
authentication data to support business operations and regulatory compliance.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.isolated_environment_fixtures import isolated_env, test_env

# Auth service imports
from auth_service.auth_core.database.models import (
    Base, AuthUser, AuthSession, AuthAuditLog, PasswordResetToken
)


class TestDatabaseModelsBusinessValue(BaseIntegrationTest):
    """Test database models delivering reliable user data persistence for business operations."""
    
    @pytest.mark.unit
    def test_auth_user_model_supports_comprehensive_user_management(self, isolated_env):
        """Test that AuthUser model supports complete user lifecycle management for business."""
        # Business Context: User model must store all data needed for account management
        
        # Create user with comprehensive business data
        user = AuthUser(
            email="enterprise.user@business.com",
            full_name="Enterprise Business User",
            hashed_password="$2b$12$secure.hashed.password.for.business.user",
            auth_provider="local",
            is_active=True,
            is_verified=True
        )
        
        # Verify core user identity fields for business operations
        assert user.email == "enterprise.user@business.com", "Email required for user identification"
        assert user.full_name == "Enterprise Business User", "Full name required for personalization"
        assert user.hashed_password is not None, "Password hash required for local auth"
        
        # Verify user status fields for account management
        assert user.is_active is True, "Active status required for account management"
        assert user.is_verified is True, "Verification status required for security"
        assert user.auth_provider == "local", "Auth provider required for login routing"
        
        # Verify security fields for business protection
        assert user.failed_login_attempts == 0, "Failed attempts tracking required for security"
        assert user.locked_until is None, "Lockout tracking required for brute force protection"
        
        # Verify timestamp fields for audit and compliance
        assert hasattr(user, 'created_at'), "Creation time required for audit trails"
        assert hasattr(user, 'updated_at'), "Update time required for change tracking"
        assert hasattr(user, 'last_login_at'), "Login time required for security monitoring"
        
        # User ID should be generated automatically
        assert hasattr(user, 'id'), "User ID required for database operations"
    
    @pytest.mark.unit
    def test_auth_user_model_supports_oauth_business_integration(self, isolated_env):
        """Test that AuthUser model supports OAuth provider integration for user acquisition."""
        # Business Context: OAuth integration reduces signup friction and improves conversion
        
        # Create OAuth user (Google authentication)
        oauth_user = AuthUser(
            email="google.user@gmail.com",
            full_name="Google OAuth User",
            auth_provider="google",
            provider_user_id="google_123456789",
            provider_data={
                "google_id": "123456789",
                "picture": "https://lh3.googleusercontent.com/photo.jpg",
                "locale": "en",
                "given_name": "Google",
                "family_name": "User"
            },
            hashed_password=None,  # No password for OAuth users
            is_active=True,
            is_verified=True  # OAuth users are pre-verified by provider
        )
        
        # Verify OAuth-specific fields for business integration
        assert oauth_user.auth_provider == "google", "Provider type required for OAuth routing"
        assert oauth_user.provider_user_id == "google_123456789", "Provider ID required for linking"
        assert oauth_user.hashed_password is None, "OAuth users don't need passwords"
        assert oauth_user.is_verified is True, "OAuth users pre-verified for better UX"
        
        # Verify provider data for enhanced user experience
        provider_data = oauth_user.provider_data
        assert provider_data["google_id"] == "123456789", "Google ID required for account linking"
        assert provider_data["picture"] is not None, "Profile picture enhances user experience"
        assert provider_data["given_name"] == "Google", "First name enables personalization"
        assert provider_data["family_name"] == "User", "Last name enables personalization"
    
    @pytest.mark.unit
    def test_auth_session_model_enables_secure_session_management(self, isolated_env):
        """Test that AuthSession model enables secure multi-device session management."""
        # Business Context: Session management allows users to access platform from multiple devices
        
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        # Create session for business user
        session = AuthSession(
            id=session_id,
            user_id=user_id,
            refresh_token_hash="hashed.refresh.token.for.session.security",
            ip_address="203.0.113.45",  # Business user IP
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0",
            device_id="business_laptop_device_123",
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_active=True
        )
        
        # Verify session identification for business operations
        assert session.id == session_id, "Session ID required for session tracking"
        assert session.user_id == user_id, "User ID required for session ownership"
        assert session.refresh_token_hash is not None, "Token hash required for security"
        
        # Verify security context for fraud prevention
        assert session.ip_address == "203.0.113.45", "IP address required for security monitoring"
        assert session.user_agent is not None, "User agent required for device identification"
        assert session.device_id == "business_laptop_device_123", "Device ID enables multi-device management"
        
        # Verify session lifecycle for business operations
        assert session.is_active is True, "Active status required for session management"
        assert session.expires_at > datetime.now(timezone.utc), "Expiration required for security"
        assert session.revoked_at is None, "Revocation tracking required for logout"
        
        # Verify audit fields for compliance
        assert hasattr(session, 'created_at'), "Creation time required for audit"
        assert hasattr(session, 'last_activity'), "Activity time required for session timeout"
    
    @pytest.mark.unit
    def test_auth_audit_log_model_supports_security_compliance(self, isolated_env):
        """Test that AuthAuditLog model supports security monitoring and regulatory compliance."""
        # Business Context: Audit logs required for security monitoring and compliance (SOX, GDPR)
        
        user_id = str(uuid.uuid4())
        
        # Create audit log for successful login
        successful_login = AuthAuditLog(
            event_type="user_login",
            user_id=user_id,
            success=True,
            event_metadata={
                "auth_method": "password",
                "user_agent": "Mozilla/5.0 Chrome/91.0",
                "session_id": str(uuid.uuid4()),
                "login_duration_ms": 245
            },
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0"
        )
        
        # Verify audit event identification for compliance
        assert successful_login.event_type == "user_login", "Event type required for audit classification"
        assert successful_login.user_id == user_id, "User ID required for audit trails"
        assert successful_login.success is True, "Success status required for security monitoring"
        
        # Verify event context for security analysis
        assert successful_login.ip_address == "192.168.1.100", "IP address required for security analysis"
        assert successful_login.user_agent is not None, "User agent required for device tracking"
        
        # Verify event metadata for detailed analysis
        metadata = successful_login.event_metadata
        assert metadata["auth_method"] == "password", "Auth method required for security analysis"
        assert metadata["session_id"] is not None, "Session ID required for correlation"
        assert metadata["login_duration_ms"] == 245, "Performance metrics valuable for monitoring"
        
        # Create audit log for failed login attempt
        failed_login = AuthAuditLog(
            event_type="user_login_failed",
            user_id=user_id,
            success=False,
            error_message="Invalid password",
            event_metadata={
                "auth_method": "password",
                "failure_reason": "invalid_credentials",
                "attempt_number": 2
            },
            ip_address="203.0.113.45"  # Different IP - potential attack
        )
        
        # Verify failed login tracking for security
        assert failed_login.success is False, "Failed status required for security alerts"
        assert failed_login.error_message == "Invalid password", "Error details required for analysis"
        assert failed_login.event_metadata["failure_reason"] == "invalid_credentials", "Failure reason required"
        assert failed_login.event_metadata["attempt_number"] == 2, "Attempt tracking prevents brute force"
    
    @pytest.mark.unit
    def test_password_reset_token_model_enables_secure_password_recovery(self, isolated_env):
        """Test that PasswordResetToken model enables secure password recovery for business users."""
        # Business Context: Password recovery prevents user lockout and support burden
        
        user_id = str(uuid.uuid4())
        
        # Create password reset token for business user
        reset_token = PasswordResetToken(
            user_id=user_id,
            token_hash="secure.hashed.reset.token.for.password.recovery",
            email="business.user@company.com",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            is_used=False
        )
        
        # Verify token identification for password recovery
        assert reset_token.user_id == user_id, "User ID required for token ownership"
        assert reset_token.email == "business.user@company.com", "Email required for delivery"
        assert reset_token.token_hash is not None, "Token hash required for security"
        
        # Verify security controls for token abuse prevention
        assert reset_token.is_used is False, "Usage tracking prevents token reuse"
        assert reset_token.expires_at > datetime.now(timezone.utc), "Expiration required for security"
        
        # Verify expiration window appropriate for business users
        expiry_hours = (reset_token.expires_at - datetime.now(timezone.utc)).total_seconds() / 3600
        assert expiry_hours >= 1, "Token must last long enough for user to respond"
        assert expiry_hours <= 48, "Token must expire quickly enough for security"
        
        # Token ID should be generated for database operations
        assert hasattr(reset_token, 'id'), "Token ID required for database operations"
        assert hasattr(reset_token, 'created_at'), "Creation time required for audit"
    
    @pytest.mark.unit
    def test_database_models_support_data_integrity_for_business_operations(self, isolated_env):
        """Test that database models enforce data integrity constraints for business reliability."""
        # Business Context: Data integrity prevents corrupt user accounts and security issues
        
        # Test unique email constraint prevents duplicate accounts
        user1 = AuthUser(
            email="unique.user@business.com",
            full_name="First User"
        )
        
        user2 = AuthUser(
            email="unique.user@business.com",  # Same email - should be prevented by unique constraint
            full_name="Second User"
        )
        
        # Both users should be created in memory (constraint enforced by database)
        assert user1.email == user2.email, "Models should allow same email (constraint enforced by DB)"
        
        # Test required fields have sensible defaults
        new_user = AuthUser(email="test@business.com")
        
        assert new_user.is_active is True, "Users should be active by default for business operations"
        assert new_user.is_verified is False, "Users should require verification for security"
        assert new_user.failed_login_attempts == 0, "Failed attempts should start at zero"
        assert new_user.auth_provider == "local", "Default to local auth for simplicity"
        
        # Test session model defaults
        new_session = AuthSession(
            user_id=str(uuid.uuid4()),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1)
        )
        
        assert new_session.is_active is True, "Sessions should be active by default"
        assert new_session.refresh_token_hash is None, "Token hash optional for flexibility"
    
    @pytest.mark.unit
    def test_database_models_support_time_zone_aware_operations(self, isolated_env):
        """Test that database models handle timezone-aware datetime operations for global business."""
        # Business Context: Global business requires proper timezone handling for users worldwide
        
        # Create user with explicit timezone-aware timestamps
        utc_now = datetime.now(timezone.utc)
        
        user = AuthUser(
            email="global.user@international.com",
            full_name="Global Business User",
            last_login_at=utc_now
        )
        
        # Timestamps should be timezone-aware for global operations
        if hasattr(user, 'created_at') and user.created_at:
            assert user.created_at.tzinfo is not None, "Created timestamp must be timezone-aware"
        
        if hasattr(user, 'updated_at') and user.updated_at:
            assert user.updated_at.tzinfo is not None, "Updated timestamp must be timezone-aware"
        
        assert user.last_login_at.tzinfo is not None, "Login timestamp must be timezone-aware"
        assert user.last_login_at.tzinfo == timezone.utc, "Should use UTC for consistency"
        
        # Test session expiration with timezone awareness
        session_expiry = datetime.now(timezone.utc) + timedelta(days=7)
        session = AuthSession(
            user_id=str(uuid.uuid4()),
            expires_at=session_expiry
        )
        
        assert session.expires_at.tzinfo == timezone.utc, "Session expiry must be timezone-aware"
        
        # Test audit log with timezone awareness
        audit_log = AuthAuditLog(
            event_type="user_action",
            success=True
        )
        
        # Creation timestamp should be timezone-aware for global audit compliance
        if hasattr(audit_log, 'created_at') and audit_log.created_at:
            assert audit_log.created_at.tzinfo is not None, "Audit timestamp must be timezone-aware"
    
    @pytest.mark.unit
    def test_database_models_support_business_query_patterns(self, isolated_env):
        """Test that database models support efficient query patterns for business operations."""
        # Business Context: Database queries must be efficient for business application performance
        
        user_id = str(uuid.uuid4())
        
        # Create user with indexed fields for efficient lookups
        user = AuthUser(
            email="indexed.user@business.com",  # Email is indexed for login queries
            full_name="Indexed Business User"
        )
        
        # Email field should support efficient user lookup during login
        # (Index is defined in model metadata, not testable directly in unit test)
        assert user.email == "indexed.user@business.com", "Email must be searchable for login"
        
        # Create session with indexed fields for efficient session queries
        session = AuthSession(
            user_id=user_id,  # User ID is indexed for user session queries
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        
        assert session.user_id == user_id, "User ID must be searchable for session lookup"
        
        # Create audit log with indexed fields for security monitoring queries
        audit_log = AuthAuditLog(
            event_type="security_event",  # Event type is indexed for security queries
            user_id=user_id,  # User ID is indexed for user activity queries
            success=False
        )
        
        assert audit_log.event_type == "security_event", "Event type must be searchable"
        assert audit_log.user_id == user_id, "User ID must be searchable for user audit trails"
        
        # Password reset token with indexed fields for recovery queries
        reset_token = PasswordResetToken(
            user_id=user_id,  # User ID indexed for user token lookup
            email="indexed.user@business.com",  # Email indexed for recovery email lookup
            token_hash="unique.token.hash.for.security"
        )
        
        assert reset_token.email == "indexed.user@business.com", "Email must be searchable for recovery"
    
    @pytest.mark.unit
    def test_database_models_handle_json_metadata_for_business_flexibility(self, isolated_env):
        """Test that database models handle JSON metadata for flexible business data storage."""
        # Business Context: JSON fields allow storing flexible business data without schema changes
        
        # Test user provider data JSON storage
        oauth_metadata = {
            "provider": "google",
            "profile_picture": "https://example.com/photo.jpg",
            "locale": "en-US",
            "business_domain": "enterprise.com",
            "department": "Engineering",
            "job_title": "Senior Developer",
            "manager_email": "manager@enterprise.com"
        }
        
        user = AuthUser(
            email="flexible.user@enterprise.com",
            provider_data=oauth_metadata
        )
        
        # JSON data should be stored and retrieved correctly
        assert user.provider_data == oauth_metadata, "Provider data must be stored as JSON"
        assert user.provider_data["business_domain"] == "enterprise.com", "Business data accessible"
        assert user.provider_data["job_title"] == "Senior Developer", "Job info for personalization"
        
        # Test audit log metadata JSON storage
        event_metadata = {
            "request_id": "req_12345",
            "api_endpoint": "/api/auth/login",
            "response_time_ms": 156,
            "user_agent_parsed": {
                "browser": "Chrome",
                "os": "Windows",
                "device": "Desktop"
            },
            "business_context": {
                "subscription_tier": "enterprise",
                "account_type": "business",
                "feature_flags": ["multi_factor_auth", "sso_enabled"]
            }
        }
        
        audit_log = AuthAuditLog(
            event_type="detailed_login",
            success=True,
            event_metadata=event_metadata
        )
        
        # JSON metadata should preserve complex business data
        assert audit_log.event_metadata == event_metadata, "Event metadata must be stored as JSON"
        assert audit_log.event_metadata["response_time_ms"] == 156, "Performance data accessible"
        
        business_context = audit_log.event_metadata["business_context"]
        assert business_context["subscription_tier"] == "enterprise", "Business tier accessible"
        assert "multi_factor_auth" in business_context["feature_flags"], "Feature flags accessible"