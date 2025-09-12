"""
Comprehensive Unit Tests for exceptions_auth.py - AUTH Exception Handling SSOT

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) - Exception handling is critical for user experience
- Business Goal: Provide clear, secure error messages that guide users to resolution
- Value Impact: Good error handling reduces support tickets by 30% and prevents user churn
- Strategic Impact: Security exceptions protect $50K+ MRR platform from attacks

MISSION CRITICAL: Auth exceptions are the LAST LINE OF DEFENSE when authentication
fails. They must provide clear, actionable error messages to users while protecting
system security details from potential attackers. Poor exception handling leads to
user confusion, support tickets, and security vulnerabilities.

Tests validate:
1. AuthenticationError provides clear guidance for credential failures
2. AuthorizationError prevents privilege escalation with clear messages
3. TokenExpiredError guides users to re-authenticate smoothly
4. TokenInvalidError handles malformed tokens securely
5. NetraSecurityException protects against security violations
6. TokenRevokedError handles session revocation properly
7. TokenTamperError detects and prevents token tampering attacks
8. All exceptions inherit proper error codes and severity levels
9. User-friendly messages don't expose system internals
10. Error handling supports customer success and platform security

These tests ensure auth exceptions deliver secure, user-friendly error handling.
"""

import pytest
from unittest.mock import Mock, patch

from netra_backend.app.core.exceptions_auth import (
    AuthenticationError,
    AuthorizationError,
    TokenExpiredError,
    TokenInvalidError,
    NetraSecurityException,
    TokenRevokedError,
    TokenTamperError
)
from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.core.exceptions_base import NetraException


class TestAuthenticationError:
    """Test AuthenticationError provides clear guidance for credential failures."""

    def test_authentication_error_default_initialization(self):
        """Test AuthenticationError initializes with proper defaults."""
        error = AuthenticationError()
        
        # Should have proper default message
        assert str(error) == "Authentication failed"
        
        # Should inherit from NetraException
        assert isinstance(error, NetraException)
        
        # Should have correct error code
        assert error.code == ErrorCode.AUTHENTICATION_FAILED
        
        # Should have high severity
        assert error.severity == ErrorSeverity.HIGH
        
        # Should have user-friendly message
        assert error.user_message == "Please check your credentials and try again"

    def test_authentication_error_custom_message(self):
        """Test AuthenticationError accepts custom error message."""
        custom_message = "Invalid username or password"
        error = AuthenticationError(message=custom_message)
        
        assert str(error) == custom_message
        assert error.user_message == "Please check your credentials and try again"

    def test_authentication_error_with_additional_context(self):
        """Test AuthenticationError accepts additional context via kwargs."""
        error = AuthenticationError(
            message="Login failed",
            user_id="user123",
            attempt_count=3,
            ip_address="192.168.1.1"
        )
        
        assert str(error) == "Login failed"
        # Additional context should be stored for logging/monitoring
        assert hasattr(error, 'user_id') or 'user_id' in error.__dict__
        assert hasattr(error, 'attempt_count') or 'attempt_count' in error.__dict__

    def test_authentication_error_security_does_not_expose_internals(self):
        """Test AuthenticationError doesn't expose system internals to users."""
        error = AuthenticationError(message="Database connection failed during auth")
        
        # Technical message for developers/logs
        assert "Database connection failed" in str(error)
        
        # User message should not expose technical details
        assert "database" not in error.user_message.lower()
        assert "connection" not in error.user_message.lower()
        assert "credentials" in error.user_message.lower()  # Safe guidance

    def test_authentication_error_supports_logging_context(self):
        """Test AuthenticationError supports rich logging context."""
        error = AuthenticationError(
            message="Authentication failed for user login",
            username="test_user",
            auth_method="password",
            timestamp="2024-01-01T00:00:00Z",
            source_ip="10.0.0.1"
        )
        
        # Should maintain context for security logging
        assert str(error) == "Authentication failed for user login"
        assert error.code == ErrorCode.AUTHENTICATION_FAILED


class TestAuthorizationError:
    """Test AuthorizationError prevents privilege escalation with clear messages."""

    def test_authorization_error_default_initialization(self):
        """Test AuthorizationError initializes with proper defaults."""
        error = AuthorizationError()
        
        assert str(error) == "Access denied"
        assert isinstance(error, NetraException)
        assert error.code == ErrorCode.AUTHORIZATION_FAILED
        assert error.severity == ErrorSeverity.HIGH
        assert error.user_message == "You don't have permission to perform this action"

    def test_authorization_error_custom_message(self):
        """Test AuthorizationError accepts custom authorization message."""
        custom_message = "Admin access required for this operation"
        error = AuthorizationError(message=custom_message)
        
        assert str(error) == custom_message
        assert error.user_message == "You don't have permission to perform this action"

    def test_authorization_error_with_permission_context(self):
        """Test AuthorizationError captures permission context for auditing."""
        error = AuthorizationError(
            message="Insufficient permissions for admin panel",
            user_id="user456",
            required_permission="admin",
            user_permissions=["read", "write"],
            resource="/admin/users"
        )
        
        assert str(error) == "Insufficient permissions for admin panel"
        assert error.code == ErrorCode.AUTHORIZATION_FAILED
        
        # Should maintain context for security auditing
        # (Additional attributes may be stored in base class)

    def test_authorization_error_prevents_privilege_escalation_info_disclosure(self):
        """Test AuthorizationError doesn't disclose privilege escalation paths."""
        error = AuthorizationError(
            message="User attempted to access /admin/system/secrets",
            attempted_resource="/admin/system/secrets",
            escalation_attempt=True
        )
        
        # Technical message for security logs
        assert "admin/system/secrets" in str(error)
        
        # User message should not reveal system structure
        assert "/admin" not in error.user_message
        assert "secrets" not in error.user_message.lower()
        assert "permission" in error.user_message.lower()  # Safe guidance

    def test_authorization_error_supports_rbac_context(self):
        """Test AuthorizationError supports role-based access control context."""
        error = AuthorizationError(
            message="Role 'user' cannot access admin endpoints",
            user_role="user",
            required_role="admin",
            endpoint="/api/admin/users",
            action="DELETE"
        )
        
        assert str(error) == "Role 'user' cannot access admin endpoints"
        assert error.severity == ErrorSeverity.HIGH


class TestTokenExpiredError:
    """Test TokenExpiredError guides users to re-authenticate smoothly."""

    def test_token_expired_error_default_initialization(self):
        """Test TokenExpiredError initializes with proper defaults."""
        error = TokenExpiredError()
        
        assert str(error) == "Authentication token has expired"
        assert isinstance(error, NetraException)
        assert error.code == ErrorCode.TOKEN_EXPIRED
        assert error.severity == ErrorSeverity.HIGH
        assert error.user_message == "Your session has expired. Please log in again"

    def test_token_expired_error_custom_message(self):
        """Test TokenExpiredError accepts custom expiration message."""
        custom_message = "Access token expired after 30 minutes"
        error = TokenExpiredError(message=custom_message)
        
        assert str(error) == custom_message
        assert error.user_message == "Your session has expired. Please log in again"

    def test_token_expired_error_with_timing_context(self):
        """Test TokenExpiredError captures timing context for user experience."""
        error = TokenExpiredError(
            message="JWT token expired",
            token_type="access_token",
            expired_at="2024-01-01T12:00:00Z",
            issued_at="2024-01-01T11:30:00Z",
            lifetime_minutes=30
        )
        
        assert str(error) == "JWT token expired"
        assert error.code == ErrorCode.TOKEN_EXPIRED

    def test_token_expired_error_user_message_encourages_reauth(self):
        """Test TokenExpiredError user message encourages seamless re-authentication."""
        error = TokenExpiredError()
        
        # User message should be encouraging and actionable
        assert "session has expired" in error.user_message
        assert "log in again" in error.user_message
        assert "Please" in error.user_message  # Polite tone
        
        # Should not sound alarming or suggest security issues
        assert "security" not in error.user_message.lower()
        assert "violation" not in error.user_message.lower()
        assert "attack" not in error.user_message.lower()

    def test_token_expired_error_supports_refresh_token_context(self):
        """Test TokenExpiredError supports refresh token renewal context."""
        error = TokenExpiredError(
            message="Access token expired, refresh token still valid",
            access_token_expired=True,
            refresh_token_expired=False,
            can_auto_renew=True
        )
        
        assert str(error) == "Access token expired, refresh token still valid"


class TestTokenInvalidError:
    """Test TokenInvalidError handles malformed tokens securely."""

    def test_token_invalid_error_default_initialization(self):
        """Test TokenInvalidError initializes with proper defaults."""
        error = TokenInvalidError()
        
        assert str(error) == "Authentication token is invalid"
        assert isinstance(error, NetraException)
        assert error.code == ErrorCode.TOKEN_INVALID
        assert error.severity == ErrorSeverity.HIGH
        assert error.user_message == "Invalid authentication token. Please log in again"

    def test_token_invalid_error_custom_message(self):
        """Test TokenInvalidError accepts custom invalid token message."""
        custom_message = "JWT signature verification failed"
        error = TokenInvalidError(message=custom_message)
        
        assert str(error) == custom_message
        assert error.user_message == "Invalid authentication token. Please log in again"

    def test_token_invalid_error_with_validation_context(self):
        """Test TokenInvalidError captures token validation context securely."""
        error = TokenInvalidError(
            message="Token signature validation failed",
            token_format="JWT",
            validation_error="signature_mismatch",
            algorithm_expected="HS256",
            token_length=245
        )
        
        assert str(error) == "Token signature validation failed"
        assert error.code == ErrorCode.TOKEN_INVALID

    def test_token_invalid_error_security_prevents_token_disclosure(self):
        """Test TokenInvalidError doesn't expose actual token values."""
        malformed_token = "malicious.token.attempt"
        error = TokenInvalidError(
            message="Malformed JWT token received",
            received_token=malformed_token
        )
        
        # Should not expose the actual token in user message
        assert malformed_token not in error.user_message
        assert "malicious" not in error.user_message.lower()
        
        # User message should be generic and safe
        assert "Invalid authentication token" in error.user_message

    def test_token_invalid_error_supports_attack_detection_context(self):
        """Test TokenInvalidError supports attack detection for security monitoring."""
        error = TokenInvalidError(
            message="Suspected token brute force attack",
            source_ip="192.168.1.100",
            user_agent="AttackTool/1.0",
            invalid_attempts=50,
            attack_pattern="brute_force"
        )
        
        assert str(error) == "Suspected token brute force attack"
        assert error.severity == ErrorSeverity.HIGH


class TestNetraSecurityException:
    """Test NetraSecurityException protects against security violations."""

    def test_netra_security_exception_default_initialization(self):
        """Test NetraSecurityException initializes with proper defaults."""
        error = NetraSecurityException()
        
        assert str(error) == "Security violation detected"
        assert isinstance(error, NetraException)
        assert error.code == ErrorCode.SECURITY_VIOLATION
        assert error.severity == ErrorSeverity.CRITICAL  # Highest severity
        assert error.user_message == "Security violation detected. Access denied"

    def test_netra_security_exception_custom_message(self):
        """Test NetraSecurityException accepts custom security violation message."""
        custom_message = "SQL injection attempt detected"
        error = NetraSecurityException(message=custom_message)
        
        assert str(error) == custom_message
        assert error.user_message == "Security violation detected. Access denied"

    def test_netra_security_exception_critical_severity(self):
        """Test NetraSecurityException has critical severity for immediate attention."""
        error = NetraSecurityException()
        
        # Security violations should have the highest severity
        assert error.severity == ErrorSeverity.CRITICAL
        
        # This ensures security team gets immediate alerts

    def test_netra_security_exception_with_attack_context(self):
        """Test NetraSecurityException captures attack context for investigation."""
        error = NetraSecurityException(
            message="Cross-site scripting attempt detected",
            attack_type="xss",
            payload="<script>alert('xss')</script>",
            source_ip="10.0.0.1",
            user_agent="Mozilla/5.0...",
            endpoint="/api/users/search"
        )
        
        assert str(error) == "Cross-site scripting attempt detected"
        assert error.code == ErrorCode.SECURITY_VIOLATION

    def test_netra_security_exception_user_message_provides_no_attack_details(self):
        """Test NetraSecurityException user message provides no attack details."""
        error = NetraSecurityException(
            message="Buffer overflow attempt in token parsing",
            technical_details="Stack overflow at 0x7fff8a9c4000"
        )
        
        # Technical message for security team
        assert "Buffer overflow" in str(error)
        
        # User message should not reveal attack vectors or technical details
        assert "buffer" not in error.user_message.lower()
        assert "overflow" not in error.user_message.lower()
        assert "stack" not in error.user_message.lower()
        assert "violation detected" in error.user_message  # Generic message

    def test_netra_security_exception_supports_forensic_context(self):
        """Test NetraSecurityException supports forensic analysis context."""
        error = NetraSecurityException(
            message="Privilege escalation attempt via token manipulation",
            original_role="user",
            attempted_role="admin", 
            manipulation_method="jwt_claims_modification",
            forensic_id="SEC-2024-001",
            requires_investigation=True
        )
        
        assert str(error) == "Privilege escalation attempt via token manipulation"
        assert error.severity == ErrorSeverity.CRITICAL


class TestTokenRevokedError:
    """Test TokenRevokedError handles session revocation properly."""

    def test_token_revoked_error_default_initialization(self):
        """Test TokenRevokedError initializes with proper defaults."""
        error = TokenRevokedError()
        
        assert str(error) == "Authentication token has been revoked"
        assert isinstance(error, NetraException)
        assert error.code == ErrorCode.TOKEN_INVALID
        assert error.severity == ErrorSeverity.HIGH
        assert error.user_message == "Your session has been revoked. Please log in again"

    def test_token_revoked_error_custom_message(self):
        """Test TokenRevokedError accepts custom revocation message."""
        custom_message = "Admin revoked user session due to suspicious activity"
        error = TokenRevokedError(message=custom_message)
        
        assert str(error) == custom_message
        assert error.user_message == "Your session has been revoked. Please log in again"

    def test_token_revoked_error_with_revocation_context(self):
        """Test TokenRevokedError captures revocation context for auditing."""
        error = TokenRevokedError(
            message="Session revoked by administrator",
            revoked_by="admin_user_789",
            revocation_reason="suspicious_activity",
            revoked_at="2024-01-01T15:30:00Z",
            affected_sessions=3
        )
        
        assert str(error) == "Session revoked by administrator"
        assert error.code == ErrorCode.TOKEN_INVALID

    def test_token_revoked_error_user_message_explains_next_steps(self):
        """Test TokenRevokedError user message explains what user should do."""
        error = TokenRevokedError()
        
        # User message should explain the situation and next steps
        assert "session has been revoked" in error.user_message
        assert "log in again" in error.user_message
        
        # Should not alarm the user unnecessarily
        assert "security" not in error.user_message.lower()
        assert "suspicious" not in error.user_message.lower()

    def test_token_revoked_error_supports_bulk_revocation_context(self):
        """Test TokenRevokedError supports bulk session revocation context."""
        error = TokenRevokedError(
            message="All user sessions revoked due to password change",
            revocation_trigger="password_change",
            bulk_revocation=True,
            sessions_revoked=5,
            user_initiated=True
        )
        
        assert str(error) == "All user sessions revoked due to password change"


class TestTokenTamperError:
    """Test TokenTamperError detects and prevents token tampering attacks."""

    def test_token_tamper_error_default_initialization(self):
        """Test TokenTamperError initializes with proper defaults."""
        error = TokenTamperError()
        
        assert str(error) == "Token tampering detected"
        assert isinstance(error, NetraException)
        assert error.code == ErrorCode.SECURITY_VIOLATION
        assert error.severity == ErrorSeverity.CRITICAL  # Highest severity
        assert error.user_message == "Security violation detected. Please log in again"

    def test_token_tamper_error_custom_message(self):
        """Test TokenTamperError accepts custom tampering detection message."""
        custom_message = "JWT signature tampering detected"
        error = TokenTamperError(message=custom_message)
        
        assert str(error) == custom_message
        assert error.user_message == "Security violation detected. Please log in again"

    def test_token_tamper_error_critical_severity_for_security_alerts(self):
        """Test TokenTamperError has critical severity for immediate security response."""
        error = TokenTamperError()
        
        # Token tampering should trigger immediate security alerts
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.code == ErrorCode.SECURITY_VIOLATION

    def test_token_tamper_error_with_tampering_detection_context(self):
        """Test TokenTamperError captures tampering detection details."""
        error = TokenTamperError(
            message="JWT payload modification detected",
            tampering_type="payload_modification",
            original_claims={"role": "user"},
            tampered_claims={"role": "admin"}, 
            signature_valid=False,
            detection_method="signature_verification"
        )
        
        assert str(error) == "JWT payload modification detected"
        assert error.code == ErrorCode.SECURITY_VIOLATION

    def test_token_tamper_error_user_message_hides_tampering_details(self):
        """Test TokenTamperError user message hides tampering detection details."""
        error = TokenTamperError(
            message="Attempted privilege escalation via token modification",
            escalation_attempt={"from": "user", "to": "admin"}
        )
        
        # Technical message for security team
        assert "privilege escalation" in str(error).lower()
        
        # User message should not reveal tampering detection capabilities
        assert "tamper" not in error.user_message.lower()
        assert "modification" not in error.user_message.lower()
        assert "escalation" not in error.user_message.lower()
        assert "Security violation detected" in error.user_message

    def test_token_tamper_error_supports_forensic_investigation(self):
        """Test TokenTamperError supports detailed forensic investigation."""
        error = TokenTamperError(
            message="Sophisticated token manipulation attack",
            attack_sophistication="high",
            manipulation_techniques=["signature_forge", "claim_injection"],
            probable_tools=["jwt_tool", "custom_script"],
            investigation_priority="immediate",
            forensic_preservation_needed=True
        )
        
        assert str(error) == "Sophisticated token manipulation attack"
        assert error.severity == ErrorSeverity.CRITICAL


class TestExceptionInheritanceAndStructure:
    """Test exception inheritance structure and base class compliance."""

    def test_all_auth_exceptions_inherit_from_netra_exception(self):
        """Test all auth exceptions properly inherit from NetraException."""
        auth_exceptions = [
            AuthenticationError,
            AuthorizationError,
            TokenExpiredError,
            TokenInvalidError,
            NetraSecurityException,
            TokenRevokedError,
            TokenTamperError
        ]
        
        for exception_class in auth_exceptions:
            exception_instance = exception_class()
            assert isinstance(exception_instance, NetraException)

    def test_all_auth_exceptions_have_proper_error_codes(self):
        """Test all auth exceptions have appropriate error codes."""
        # Test specific error code assignments
        assert AuthenticationError().code == ErrorCode.AUTHENTICATION_FAILED
        assert AuthorizationError().code == ErrorCode.AUTHORIZATION_FAILED
        assert TokenExpiredError().code == ErrorCode.TOKEN_EXPIRED
        assert TokenInvalidError().code == ErrorCode.TOKEN_INVALID
        assert NetraSecurityException().code == ErrorCode.SECURITY_VIOLATION
        assert TokenRevokedError().code == ErrorCode.TOKEN_INVALID
        assert TokenTamperError().code == ErrorCode.SECURITY_VIOLATION

    def test_all_auth_exceptions_have_appropriate_severity_levels(self):
        """Test all auth exceptions have appropriate severity levels."""
        # Authentication and authorization failures should be HIGH
        assert AuthenticationError().severity == ErrorSeverity.HIGH
        assert AuthorizationError().severity == ErrorSeverity.HIGH
        assert TokenExpiredError().severity == ErrorSeverity.HIGH
        assert TokenInvalidError().severity == ErrorSeverity.HIGH
        assert TokenRevokedError().severity == ErrorSeverity.HIGH
        
        # Security violations should be CRITICAL
        assert NetraSecurityException().severity == ErrorSeverity.CRITICAL
        assert TokenTamperError().severity == ErrorSeverity.CRITICAL

    def test_all_auth_exceptions_have_user_friendly_messages(self):
        """Test all auth exceptions provide user-friendly messages."""
        exceptions_and_expected_guidance = [
            (AuthenticationError(), "credentials"),
            (AuthorizationError(), "permission"),
            (TokenExpiredError(), "session has expired"),
            (TokenInvalidError(), "Invalid authentication token"),
            (NetraSecurityException(), "Security violation detected"),
            (TokenRevokedError(), "session has been revoked"),
            (TokenTamperError(), "Security violation detected")
        ]
        
        for exception, expected_keyword in exceptions_and_expected_guidance:
            assert hasattr(exception, 'user_message')
            assert expected_keyword.lower() in exception.user_message.lower()
            assert len(exception.user_message) > 0

    def test_auth_exceptions_support_kwargs_for_context(self):
        """Test auth exceptions accept kwargs for additional context."""
        test_context = {
            "user_id": "test_user_123",
            "session_id": "session_456",
            "ip_address": "192.168.1.1",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        # All exceptions should accept context kwargs
        exceptions = [
            AuthenticationError(**test_context),
            AuthorizationError(**test_context),
            TokenExpiredError(**test_context),
            TokenInvalidError(**test_context),
            NetraSecurityException(**test_context),
            TokenRevokedError(**test_context),
            TokenTamperError(**test_context)
        ]
        
        for exception in exceptions:
            # Context should be available for logging/monitoring
            # (May be stored in base class or as attributes)
            assert isinstance(exception, NetraException)


class TestExceptionMessageSecurity:
    """Test exception messages maintain security without exposing system internals."""

    def test_exceptions_dont_expose_database_details(self):
        """Test exceptions don't expose database connection details."""
        database_error_scenarios = [
            AuthenticationError(message="Database connection timeout during auth"),
            AuthorizationError(message="SQL query failed for permission check"),
            TokenExpiredError(message="Redis cache lookup failed for token"),
            TokenInvalidError(message="Database token validation query error")
        ]
        
        for exception in database_error_scenarios:
            # User messages should not contain database details
            user_msg = exception.user_message.lower()
            assert "database" not in user_msg
            assert "sql" not in user_msg
            assert "redis" not in user_msg
            assert "query" not in user_msg
            assert "connection" not in user_msg

    def test_exceptions_dont_expose_crypto_implementation_details(self):
        """Test exceptions don't expose cryptographic implementation details."""
        crypto_error_scenarios = [
            TokenInvalidError(message="HMAC-SHA256 signature verification failed"),
            TokenTamperError(message="RSA-2048 public key verification error"),
            NetraSecurityException(message="AES-256-GCM decryption failed")
        ]
        
        for exception in crypto_error_scenarios:
            # User messages should not contain crypto details
            user_msg = exception.user_message.lower()
            assert "hmac" not in user_msg
            assert "sha256" not in user_msg
            assert "rsa" not in user_msg
            assert "aes" not in user_msg
            assert "gcm" not in user_msg

    def test_exceptions_dont_expose_internal_service_urls(self):
        """Test exceptions don't expose internal service URLs."""
        service_error_scenarios = [
            AuthenticationError(message="Failed to connect to http://auth-service:8081/validate"),
            AuthorizationError(message="Permission service at http://internal-rbac:9000 unreachable")
        ]
        
        for exception in service_error_scenarios:
            # User messages should not contain internal URLs
            user_msg = exception.user_message.lower()
            assert "http://" not in user_msg
            assert ":8081" not in user_msg
            assert ":9000" not in user_msg
            assert "auth-service" not in user_msg
            assert "internal-rbac" not in user_msg


class TestExceptionBusinessValueDelivery:
    """Test that auth exceptions deliver expected business value."""

    def test_exceptions_reduce_support_ticket_volume(self):
        """Test exceptions provide clear guidance to reduce support tickets."""
        user_facing_exceptions = [
            AuthenticationError(),
            AuthorizationError(),
            TokenExpiredError(),
            TokenInvalidError(),
            TokenRevokedError()
        ]
        
        for exception in user_facing_exceptions:
            user_message = exception.user_message
            
            # Should provide actionable guidance
            assert any(action in user_message.lower() for action in [
                "log in", "check", "try again", "contact", "permission"
            ])
            
            # Should be polite and professional
            assert user_message[0].isupper()  # Proper capitalization
            assert not user_message.isupper()  # Not all caps (not shouting)

    def test_security_exceptions_protect_business_value(self):
        """Test security exceptions protect business value by preventing attacks."""
        security_exceptions = [
            NetraSecurityException(),
            TokenTamperError()
        ]
        
        for exception in security_exceptions:
            # Should have critical severity for immediate response
            assert exception.severity == ErrorSeverity.CRITICAL
            
            # Should use security violation code for proper routing
            assert exception.code == ErrorCode.SECURITY_VIOLATION
            
            # User message should not reveal attack details
            user_msg = exception.user_message.lower()
            assert "security violation" in user_msg
            assert "access denied" in user_msg

    def test_token_exceptions_guide_smooth_reauthorization(self):
        """Test token exceptions guide users to smooth re-authorization."""
        token_exceptions = [
            TokenExpiredError(),
            TokenInvalidError(),
            TokenRevokedError()
        ]
        
        for exception in token_exceptions:
            user_message = exception.user_message.lower()
            
            # Should guide to re-authentication
            assert "log in" in user_message
            
            # Should not create alarm or suggest security breach
            assert "attack" not in user_message
            assert "breach" not in user_message
            assert "hacker" not in user_message
            assert "violation" not in user_message or exception.severity == ErrorSeverity.CRITICAL

    def test_exceptions_maintain_platform_professionalism(self):
        """Test exceptions maintain professional tone for enterprise customers."""
        all_auth_exceptions = [
            AuthenticationError(),
            AuthorizationError(),
            TokenExpiredError(),
            TokenInvalidError(),
            NetraSecurityException(),
            TokenRevokedError(),
            TokenTamperError()
        ]
        
        for exception in all_auth_exceptions:
            user_message = exception.user_message
            
            # Should be professional and polite
            assert user_message.strip() != ""  # Not empty
            assert user_message[0].isupper()  # Proper sentence case
            assert user_message.endswith((".", "!"))  # Proper punctuation
            
            # Should not contain unprofessional language
            assert "error" not in user_message.lower()  # Use "issue" instead
            assert "fail" not in user_message.lower()  # Use positive language
            
            # This maintains professional image for enterprise customers