"""
Comprehensive Unit Tests for auth_integration/validators.py - AUTH Validation SSOT

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) - Auth validation is security foundation
- Business Goal: Prevent security vulnerabilities and reduce auth errors by 15-20%
- Value Impact: Proper validation protects $50K+ MRR AI optimization platform
- Strategic Impact: Validation prevents injection attacks, ensures GDPR compliance

MISSION CRITICAL: Auth validators are the first line of defense against security
attacks. They prevent SQL injection, XSS, password attacks, and ensure proper
email/token/permission validation. Without proper validation, the entire platform
is vulnerable to security breaches.

Tests validate:
1. Email validation prevents injection attacks and follows RFC standards
2. Password validation enforces NIST security requirements
3. Token validation prevents malformed JWT attacks
4. Permission validation ensures proper access control
5. Service ID validation prevents inter-service auth failures
6. Input sanitization prevents XSS and injection attacks
7. IP address validation supports audit and security logging
8. Error handling provides consistent, secure error messages

These tests ensure validation business logic protects user data and platform security.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from netra_backend.app.auth_integration.validators import (
    validate_email_format,
    validate_password_strength,
    validate_token_format,
    validate_service_id,
    validate_permission_format,
    validate_session_metadata,
    validate_ip_address,
    validate_user_agent,
    validate_audit_event_type,
    validate_auth_provider,
    validate_token_type,
    validate_expires_at,
    validate_oauth_token,
    validate_error_code,
    validate_endpoint_url,
    validate_cors_origin,
    sanitize_user_input,
    validate_permission_list,
    validate_auth_request_timing,
    create_validation_error,
    validate_model_field,
    AuthValidationError,
    _check_password_character_requirements,
    _check_token_length,
    _check_service_id_length,
    _check_permission_length,
    _validate_ip_format,
    _is_valid_ipv4,
    _is_valid_ipv6,
    _check_max_expiry,
    _check_oauth_token_length,
    _check_error_code_length,
    _check_url_length,
    _validate_origin_format,
    _is_valid_domain,
    _process_sanitization
)


class TestEmailValidation:
    """Test email validation prevents injection attacks and follows RFC standards."""

    def test_validate_email_format_accepts_valid_emails(self):
        """Test email validator accepts valid RFC-compliant emails."""
        valid_emails = [
            "test@example.com",
            "user+tag@domain.org",
            "first.last@subdomain.example.com",
            "admin@company-name.co.uk",
            "123@numbers.net",
            "a@b.co"  # Minimal valid email
        ]
        
        for email in valid_emails:
            assert validate_email_format(email) is True, f"Should accept valid email: {email}"

    def test_validate_email_format_rejects_invalid_emails(self):
        """Test email validator rejects invalid emails that could be injection attempts."""
        invalid_emails = [
            "not-an-email",
            "@domain.com",
            "user@",
            "user@@domain.com",
            "user@domain",
            "user name@domain.com",  # Space not allowed
            "user@domain.com; DROP TABLE users;",  # SQL injection attempt
            "<script>alert('xss')</script>@domain.com",  # XSS attempt
            "user@domain..com",  # Double dots
            "",
            None
        ]
        
        for email in invalid_emails:
            if email is not None:
                assert validate_email_format(email) is False, f"Should reject invalid email: {email}"
            else:
                with pytest.raises((TypeError, AttributeError)):
                    validate_email_format(email)

    def test_validate_email_format_prevents_injection_attacks(self):
        """Test email validator prevents common injection attack patterns."""
        injection_attempts = [
            "user@domain.com'; DROP TABLE users; --",
            "user@domain.com<script>alert(1)</script>",
            "user@domain.com\"><img src=x onerror=alert(1)>",
            "user@domain.com\nBcc: admin@evil.com",  # Header injection
            "user@domain.com\r\nTo: victim@target.com"  # CRLF injection
        ]
        
        for injection in injection_attempts:
            assert validate_email_format(injection) is False, f"Should block injection: {injection}"


class TestPasswordValidation:
    """Test password validation enforces NIST security requirements."""

    def test_validate_password_strength_enforces_minimum_length(self):
        """Test password validator enforces 8-character minimum (NIST standard)."""
        # Too short passwords
        short_passwords = ["", "a", "12", "abc", "Abc1", "ShOrT7"]
        
        for password in short_passwords:
            result = validate_password_strength(password)
            assert result["valid"] is False
            assert "too short" in result["error"].lower()

    def test_validate_password_strength_enforces_character_requirements(self):
        """Test password validator enforces character diversity requirements."""
        # Missing uppercase
        result = validate_password_strength("lowercase123")
        assert result["valid"] is False
        assert "uppercase" in result["error"].lower()
        
        # Missing lowercase  
        result = validate_password_strength("UPPERCASE123")
        assert result["valid"] is False
        assert "lowercase" in result["error"].lower()
        
        # Missing numbers
        result = validate_password_strength("UpperLower")
        assert result["valid"] is False
        assert "number" in result["error"].lower()

    def test_validate_password_strength_accepts_strong_passwords(self):
        """Test password validator accepts strong passwords."""
        strong_passwords = [
            "Password123",
            "MySecure1Pass",
            "Complex9Password",
            "StrongAuth2024!",
            "Business1Value"
        ]
        
        for password in strong_passwords:
            result = validate_password_strength(password)
            assert result["valid"] is True, f"Should accept strong password: {password}"
            assert result["error"] is None

    def test_check_password_character_requirements_validates_diversity(self):
        """Test internal character requirement checker validates password diversity."""
        # Valid password with all requirements
        result = _check_password_character_requirements("Password123")
        assert result["valid"] is True
        assert result["error"] is None
        
        # Test each missing character type
        test_cases = [
            ("lowercase123", "uppercase"),
            ("UPPERCASE123", "lowercase"),
            ("NoNumbers", "number")
        ]
        
        for password, missing_type in test_cases:
            result = _check_password_character_requirements(password)
            assert result["valid"] is False
            assert missing_type.lower() in result["error"].lower()


class TestTokenValidation:
    """Test token validation prevents malformed JWT attacks."""

    def test_validate_token_format_accepts_valid_jwt_structure(self):
        """Test token validator accepts valid JWT structure (3 parts)."""
        valid_jwt_tokens = [
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature",
            "header.payload.signature",
            "part1.part2.part3WithLongerContent",
            "a.b.c",  # Minimal valid structure
        ]
        
        for token in valid_jwt_tokens:
            assert validate_token_format(token) is True, f"Should accept valid JWT: {token}"

    def test_validate_token_format_rejects_malformed_tokens(self):
        """Test token validator rejects malformed tokens that could be attack attempts."""
        invalid_tokens = [
            "",
            "not.a.jwt",  # Only 2 parts
            "not.a.jwt.token.extra",  # More than 3 parts
            "single-part-token",
            "two.parts",
            ".",  # Empty parts
            "..",  # Empty parts
            "part1.",  # Missing parts
            ".part2.part3",  # Empty first part
            None
        ]
        
        for token in invalid_tokens:
            if token is not None:
                assert validate_token_format(token) is False, f"Should reject invalid token: {token}"
            else:
                with pytest.raises((TypeError, AttributeError)):
                    validate_token_format(token)

    def test_check_token_length_enforces_minimum_length(self):
        """Test token length checker enforces minimum length for security."""
        # Too short tokens (potential brute force targets)
        assert _check_token_length("short") is False
        assert _check_token_length("a.b.c") is False  # Valid structure but too short
        
        # Acceptable length tokens
        assert _check_token_length("this.is.a.longer.token.that.meets.minimum.length.requirements") is True
        assert _check_token_length("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature") is True


class TestServiceValidation:
    """Test service ID validation prevents inter-service auth failures."""

    def test_validate_service_id_accepts_valid_service_names(self):
        """Test service ID validator accepts valid service names."""
        valid_service_ids = [
            "netra-backend",
            "auth-service", 
            "user_service",
            "analytics-api",
            "web123",
            "service_1",
            "backend-v2"
        ]
        
        for service_id in valid_service_ids:
            assert validate_service_id(service_id) is True, f"Should accept valid service ID: {service_id}"

    def test_validate_service_id_rejects_invalid_service_names(self):
        """Test service ID validator rejects invalid or dangerous service names."""
        invalid_service_ids = [
            "",
            "ab",  # Too short
            "service with spaces",  # Spaces not allowed
            "service@domain",  # Special chars not allowed
            "service.name",  # Dots not allowed
            "service/path",  # Slashes not allowed
            "../service",  # Path traversal attempt
            "service; rm -rf /",  # Command injection attempt
            None,
            "a" * 60  # Too long
        ]
        
        for service_id in invalid_service_ids:
            if service_id is not None:
                assert validate_service_id(service_id) is False, f"Should reject invalid service ID: {service_id}"
            else:
                with pytest.raises((TypeError, AttributeError)):
                    validate_service_id(service_id)

    def test_check_service_id_length_enforces_reasonable_bounds(self):
        """Test service ID length checker enforces reasonable length bounds."""
        # Too short
        assert _check_service_id_length("ab") is False
        assert _check_service_id_length("") is False
        
        # Just right
        assert _check_service_id_length("abc") is True  # Minimum length
        assert _check_service_id_length("service-name-that-is-reasonable") is True
        assert _check_service_id_length("a" * 50) is True  # Maximum length
        
        # Too long  
        assert _check_service_id_length("a" * 51) is False


class TestPermissionValidation:
    """Test permission validation ensures proper access control."""

    def test_validate_permission_format_accepts_valid_permissions(self):
        """Test permission validator accepts valid permission strings."""
        valid_permissions = [
            "read",
            "write",
            "admin",
            "users:read",
            "agents:write",
            "system:admin",
            "analytics.view",
            "cost-optimization:execute",
            "api_access",
            "user_management"
        ]
        
        for permission in valid_permissions:
            assert validate_permission_format(permission) is True, f"Should accept valid permission: {permission}"

    def test_validate_permission_format_rejects_invalid_permissions(self):
        """Test permission validator rejects invalid or dangerous permissions."""
        invalid_permissions = [
            "",
            "permission with spaces",  # Spaces not allowed
            "permission@evil.com",  # @ not allowed
            "permission#hash",  # # not allowed  
            "permission<script>",  # < > not allowed
            "../admin",  # Path traversal
            "permission; rm -rf /",  # Command injection
            "a" * 200,  # Too long
            None
        ]
        
        for permission in invalid_permissions:
            if permission is not None:
                assert validate_permission_format(permission) is False, f"Should reject invalid permission: {permission}"
            else:
                with pytest.raises((TypeError, AttributeError)):
                    validate_permission_format(permission)

    def test_check_permission_length_enforces_reasonable_limit(self):
        """Test permission length checker prevents DoS attacks."""
        # Reasonable length permissions
        assert _check_permission_length("read") is True
        assert _check_permission_length("users:read:write:admin") is True
        assert _check_permission_length("a" * 100) is True  # Maximum length
        
        # Too long permissions (potential DoS)
        assert _check_permission_length("a" * 101) is False

    def test_validate_permission_list_validates_permission_arrays(self):
        """Test permission list validator ensures valid permission arrays."""
        # Valid permission lists
        valid_lists = [
            ["read", "write"],
            ["users:read", "agents:write", "system:admin"],
            [],  # Empty list is valid
            ["single_permission"]
        ]
        
        for perm_list in valid_lists:
            assert validate_permission_list(perm_list) is True, f"Should accept valid permission list: {perm_list}"

    def test_validate_permission_list_rejects_invalid_arrays(self):
        """Test permission list validator rejects invalid or dangerous arrays."""
        # Invalid permission lists
        invalid_lists = [
            "not_a_list",  # Not a list
            ["valid", "invalid permission with spaces"],  # Contains invalid permission
            ["read"] * 60,  # Too many permissions (potential DoS)
            [123, "read"],  # Non-string permissions
            None
        ]
        
        for perm_list in invalid_lists:
            if perm_list is not None:
                assert validate_permission_list(perm_list) is False, f"Should reject invalid permission list: {perm_list}"
            else:
                with pytest.raises((TypeError, AttributeError)):
                    validate_permission_list(perm_list)


class TestIPAddressValidation:
    """Test IP address validation supports audit and security logging."""

    def test_validate_ip_address_accepts_valid_ipv4_addresses(self):
        """Test IP validator accepts valid IPv4 addresses."""
        valid_ipv4 = [
            "127.0.0.1",
            "192.168.1.1",
            "10.0.0.1", 
            "172.16.0.1",
            "8.8.8.8",
            "255.255.255.255"
        ]
        
        for ip in valid_ipv4:
            assert validate_ip_address(ip) is True, f"Should accept valid IPv4: {ip}"

    def test_validate_ip_address_accepts_valid_ipv6_addresses(self):
        """Test IP validator accepts valid IPv6 addresses."""
        valid_ipv6 = [
            "::1",
            "2001:db8::1",
            "fe80::1",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "::ffff:192.168.1.1"  # IPv4-mapped IPv6
        ]
        
        for ip in valid_ipv6:
            assert validate_ip_address(ip) is True, f"Should accept valid IPv6: {ip}"

    def test_validate_ip_address_accepts_empty_string_as_optional(self):
        """Test IP validator treats empty string as optional field."""
        assert validate_ip_address("") is True  # Optional field
        assert validate_ip_address(None) is True  # None should be handled gracefully

    def test_validate_ip_address_rejects_invalid_addresses(self):
        """Test IP validator rejects invalid IP addresses."""
        invalid_ips = [
            "256.256.256.256",  # IPv4 out of range
            "192.168.1",  # Incomplete IPv4
            "192.168.1.1.1",  # Too many octets
            "not.an.ip.address",
            "malicious_input",
            "192.168.1.1; DROP TABLE users;"  # SQL injection attempt
        ]
        
        for ip in invalid_ips:
            assert validate_ip_address(ip) is False, f"Should reject invalid IP: {ip}"

    def test_is_valid_ipv4_validates_ipv4_format_correctly(self):
        """Test IPv4 validator correctly validates IPv4 format and ranges."""
        # Valid IPv4 addresses
        assert _is_valid_ipv4("127.0.0.1") is True
        assert _is_valid_ipv4("0.0.0.0") is True
        assert _is_valid_ipv4("255.255.255.255") is True
        
        # Invalid IPv4 addresses
        assert _is_valid_ipv4("256.1.1.1") is False  # Out of range
        assert _is_valid_ipv4("192.168.1") is False  # Too few octets
        assert _is_valid_ipv4("192.168.1.1.1") is False  # Too many octets
        assert _is_valid_ipv4("not.an.ip") is False

    def test_is_valid_ipv6_validates_ipv6_format_correctly(self):
        """Test IPv6 validator correctly validates IPv6 format."""
        # Valid IPv6 addresses
        assert _is_valid_ipv6("::1") is True
        assert _is_valid_ipv6("2001:db8::1") is True
        
        # Invalid IPv6 addresses (basic validation)
        assert _is_valid_ipv6("192.168.1.1") is False  # IPv4
        assert _is_valid_ipv6("not.an.ipv6") is False


class TestSessionAndMetadataValidation:
    """Test session metadata validation prevents DoS and injection attacks."""

    def test_validate_session_metadata_accepts_valid_metadata(self):
        """Test session metadata validator accepts valid metadata dictionaries."""
        valid_metadata = [
            {},  # Empty metadata
            {"browser": "Chrome", "version": "91.0"},
            {"ip": "127.0.0.1", "user_agent": "Mozilla/5.0"},
            {"session_id": "abc123", "csrf_token": "token123"}
        ]
        
        for metadata in valid_metadata:
            assert validate_session_metadata(metadata) is True, f"Should accept valid metadata: {metadata}"

    def test_validate_session_metadata_rejects_invalid_metadata(self):
        """Test session metadata validator prevents DoS attacks."""
        # Invalid metadata types
        assert validate_session_metadata("not_a_dict") is False
        assert validate_session_metadata(None) is False
        assert validate_session_metadata([1, 2, 3]) is False
        
        # Oversized metadata (DoS prevention)
        huge_metadata = {"key": "x" * 2000}  # Creates very large dict
        assert validate_session_metadata(huge_metadata) is False

    def test_validate_user_agent_handles_optional_field_correctly(self):
        """Test user agent validator handles optional field correctly."""
        # Valid user agents
        assert validate_user_agent("") is True  # Empty is valid (optional)
        assert validate_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") is True
        assert validate_user_agent("Chrome/91.0.4472.124") is True
        
        # Invalid user agents (too long - DoS prevention)
        long_user_agent = "x" * 600  # Exceeds 500 char limit
        assert validate_user_agent(long_user_agent) is False


class TestAuditAndEventValidation:
    """Test audit event validation ensures proper security logging."""

    def test_validate_audit_event_type_accepts_valid_events(self):
        """Test audit event validator accepts valid security event types."""
        valid_events = [
            "login", "logout", "token_refresh", "token_validate",
            "password_change", "profile_update", "permission_grant",
            "permission_revoke", "session_create", "session_destroy"
        ]
        
        for event in valid_events:
            assert validate_audit_event_type(event) is True, f"Should accept valid event: {event}"

    def test_validate_audit_event_type_rejects_invalid_events(self):
        """Test audit event validator rejects invalid or dangerous event types."""
        invalid_events = [
            "",
            "invalid_event",
            "login; DROP TABLE audit_log;",  # SQL injection attempt
            "<script>alert('xss')</script>",  # XSS attempt
            "custom_event",
            None
        ]
        
        for event in invalid_events:
            if event is not None:
                assert validate_audit_event_type(event) is False, f"Should reject invalid event: {event}"
            else:
                with pytest.raises((TypeError, AttributeError)):
                    validate_audit_event_type(event)

    def test_validate_auth_provider_accepts_supported_providers(self):
        """Test auth provider validator accepts supported authentication providers."""
        valid_providers = ["local", "google", "github", "api_key"]
        
        for provider in valid_providers:
            assert validate_auth_provider(provider) is True, f"Should accept valid provider: {provider}"

    def test_validate_auth_provider_rejects_unsupported_providers(self):
        """Test auth provider validator rejects unsupported providers."""
        invalid_providers = [
            "",
            "facebook",  # Not supported
            "microsoft",  # Not supported  
            "evil_provider",
            "provider; DROP TABLE users;",
            None
        ]
        
        for provider in invalid_providers:
            if provider is not None:
                assert validate_auth_provider(provider) is False, f"Should reject invalid provider: {provider}"
            else:
                with pytest.raises((TypeError, AttributeError)):
                    validate_auth_provider(provider)

    def test_validate_token_type_accepts_supported_token_types(self):
        """Test token type validator accepts supported JWT token types."""
        valid_types = ["access", "refresh", "service"]
        
        for token_type in valid_types:
            assert validate_token_type(token_type) is True, f"Should accept valid token type: {token_type}"

    def test_validate_token_type_rejects_unsupported_types(self):
        """Test token type validator rejects unsupported token types."""
        invalid_types = [
            "",
            "bearer",  # Not a token type
            "custom",
            "type; DROP TABLE tokens;",
            None
        ]
        
        for token_type in invalid_types:
            if token_type is not None:
                assert validate_token_type(token_type) is False, f"Should reject invalid token type: {token_type}"
            else:
                with pytest.raises((TypeError, AttributeError)):
                    validate_token_type(token_type)


class TestTimingValidation:
    """Test timing validation prevents replay attacks and clock skew issues."""

    def test_validate_expires_at_accepts_future_timestamps(self):
        """Test expiry validator accepts reasonable future timestamps."""
        now = datetime.now(timezone.utc)
        future_times = [
            now + timedelta(minutes=30),
            now + timedelta(hours=1),
            now + timedelta(days=1),
            now + timedelta(days=30),
            now + timedelta(days=365)  # Maximum allowed
        ]
        
        for expiry in future_times:
            assert validate_expires_at(expiry) is True, f"Should accept future time: {expiry}"

    def test_validate_expires_at_rejects_past_timestamps(self):
        """Test expiry validator rejects past timestamps (expired tokens)."""
        now = datetime.now(timezone.utc)
        past_times = [
            now - timedelta(seconds=1),
            now - timedelta(minutes=30),
            now - timedelta(hours=1),
            now - timedelta(days=1)
        ]
        
        for expiry in past_times:
            assert validate_expires_at(expiry) is False, f"Should reject past time: {expiry}"

    def test_validate_expires_at_rejects_excessive_future_timestamps(self):
        """Test expiry validator prevents excessively long-lived tokens."""
        now = datetime.now(timezone.utc)
        excessive_times = [
            now + timedelta(days=366),  # Over 1 year
            now + timedelta(days=1000),
            now + timedelta(days=365*10)  # 10 years
        ]
        
        for expiry in excessive_times:
            assert validate_expires_at(expiry) is False, f"Should reject excessive future time: {expiry}"

    def test_check_max_expiry_enforces_one_year_maximum(self):
        """Test maximum expiry checker enforces 1-year maximum token lifetime."""
        now = datetime.now(timezone.utc)
        
        # Within 1 year limit
        assert _check_max_expiry(now + timedelta(days=364)) is True
        assert _check_max_expiry(now + timedelta(days=365)) is True
        
        # Beyond 1 year limit
        assert _check_max_expiry(now + timedelta(days=366)) is False

    def test_validate_auth_request_timing_prevents_replay_attacks(self):
        """Test auth request timing validator prevents replay attacks."""
        now = datetime.now(timezone.utc)
        
        # Recent requests (within 5 minutes) are valid
        recent_times = [
            now,
            now - timedelta(seconds=30),
            now - timedelta(minutes=2),
            now - timedelta(minutes=5)  # Exactly at boundary
        ]
        
        for request_time in recent_times:
            assert validate_auth_request_timing(request_time) is True, f"Should accept recent time: {request_time}"

    def test_validate_auth_request_timing_rejects_old_requests(self):
        """Test auth request timing validator rejects old requests (replay protection)."""
        now = datetime.now(timezone.utc)
        
        # Old requests (beyond 5 minutes) are invalid
        old_times = [
            now - timedelta(minutes=6),
            now - timedelta(hours=1),
            now - timedelta(days=1)
        ]
        
        for request_time in old_times:
            assert validate_auth_request_timing(request_time) is False, f"Should reject old time: {request_time}"


class TestInputSanitization:
    """Test input sanitization prevents XSS and injection attacks."""

    def test_sanitize_user_input_removes_dangerous_characters(self):
        """Test input sanitizer removes characters used in XSS and injection attacks."""
        dangerous_inputs = [
            ("<script>alert('xss')</script>", "scriptalert('xss')/script"),
            ("user'; DROP TABLE users; --", "user' DROP TABLE users --"),
            ('onclick="malicious()"', 'onclick=malicious()'),
            ("<img src=x onerror=alert(1)>", "img src=x onerror=alert(1)"),
            ("normal text", "normal text")  # Normal text unchanged
        ]
        
        for dangerous, expected_safe in dangerous_inputs:
            sanitized = sanitize_user_input(dangerous)
            assert sanitized == expected_safe, f"Should sanitize: {dangerous} -> {expected_safe}"

    def test_sanitize_user_input_enforces_length_limits(self):
        """Test input sanitizer prevents DoS attacks via length limits."""
        # Default max length (100 chars)
        long_input = "x" * 200
        sanitized = sanitize_user_input(long_input)
        assert len(sanitized) <= 100
        
        # Custom max length
        sanitized_custom = sanitize_user_input(long_input, max_length=50)
        assert len(sanitized_custom) <= 50

    def test_sanitize_user_input_handles_empty_and_none_inputs(self):
        """Test input sanitizer handles edge cases gracefully."""
        assert sanitize_user_input("") == ""
        assert sanitize_user_input(None) == ""

    def test_process_sanitization_removes_specific_characters(self):
        """Test internal sanitization process removes specific dangerous characters."""
        test_cases = [
            ("normal text", "normal text"),
            ("<>\"';", ""),  # All dangerous chars removed
            ("mix<ed>content", "mixedcontent"),
            ("   spaces   ", "spaces")  # Whitespace trimmed
        ]
        
        for input_str, expected in test_cases:
            result = _process_sanitization(input_str, 100)
            assert result == expected, f"Should process: {input_str} -> {expected}"


class TestURLAndOriginValidation:
    """Test URL and CORS origin validation prevents security misconfigurations."""

    def test_validate_endpoint_url_accepts_valid_urls(self):
        """Test URL validator accepts valid HTTP/HTTPS URLs."""
        valid_urls = [
            "https://api.example.com",
            "http://localhost:8080", 
            "https://auth-service:8081/auth",
            "https://subdomain.example.com/path",
            "http://192.168.1.1:3000"
        ]
        
        for url in valid_urls:
            assert validate_endpoint_url(url) is True, f"Should accept valid URL: {url}"

    def test_validate_endpoint_url_rejects_invalid_urls(self):
        """Test URL validator rejects invalid or dangerous URLs."""
        invalid_urls = [
            "",
            "not-a-url",
            "ftp://example.com",  # Wrong protocol
            "javascript:alert(1)",  # XSS attempt
            "https://",  # Incomplete
            "https://example.com" + "x" * 300,  # Too long
            None
        ]
        
        for url in invalid_urls:
            if url is not None:
                assert validate_endpoint_url(url) is False, f"Should reject invalid URL: {url}"
            else:
                with pytest.raises((TypeError, AttributeError)):
                    validate_endpoint_url(url)

    def test_check_url_length_prevents_dos_attacks(self):
        """Test URL length checker prevents DoS attacks via oversized URLs."""
        # Reasonable length URLs
        assert _check_url_length("https://example.com") is True
        assert _check_url_length("x" * 200) is True  # Maximum length
        
        # Oversized URLs (potential DoS)
        assert _check_url_length("x" * 201) is False

    def test_validate_cors_origin_accepts_valid_origins(self):
        """Test CORS origin validator accepts valid origin patterns."""
        valid_origins = [
            "*",  # Wildcard (allowed but not recommended)
            "https://app.example.com",
            "http://localhost:3000",
            "example.com",  # Domain only
            "subdomain.example.co.uk"
        ]
        
        for origin in valid_origins:
            assert validate_cors_origin(origin) is True, f"Should accept valid origin: {origin}"

    def test_validate_cors_origin_rejects_invalid_origins(self):
        """Test CORS origin validator rejects invalid or dangerous origins."""
        invalid_origins = [
            "",
            "javascript:alert(1)",  # XSS attempt
            "data:text/html,<script>alert(1)</script>",  # Data URI XSS
            "invalid-domain",  # Invalid domain
            None
        ]
        
        for origin in invalid_origins:
            if origin is not None:
                assert validate_cors_origin(origin) is False, f"Should reject invalid origin: {origin}"
            else:
                with pytest.raises((TypeError, AttributeError)):
                    validate_cors_origin(origin)

    def test_is_valid_domain_validates_domain_format(self):
        """Test domain validator correctly validates domain name format."""
        # Valid domains
        assert _is_valid_domain("example.com") is True
        assert _is_valid_domain("subdomain.example.co.uk") is True
        assert _is_valid_domain("api.service-name.com") is True
        
        # Invalid domains
        assert _is_valid_domain("invalid-domain") is False
        assert _is_valid_domain("domain.") is False
        assert _is_valid_domain(".example.com") is False


class TestOAuthTokenValidation:
    """Test OAuth token validation prevents token-based attacks."""

    def test_validate_oauth_token_accepts_valid_tokens(self):
        """Test OAuth token validator accepts valid OAuth token formats."""
        valid_oauth_tokens = [
            "ya29.a0AfH6SMC...",  # Google OAuth token pattern
            "gho_16C7e42F292c6912E7710c838347Ae178B4a",  # GitHub OAuth token pattern
            "access_token_1234567890",
            "oauth2_token_abcdefghijklmnop"
        ]
        
        for token in valid_oauth_tokens:
            assert validate_oauth_token(token) is True, f"Should accept valid OAuth token: {token}"

    def test_validate_oauth_token_rejects_invalid_tokens(self):
        """Test OAuth token validator rejects invalid or suspicious tokens."""
        invalid_oauth_tokens = [
            "",
            "short",  # Too short
            "x" * 2100,  # Too long (potential DoS)
            None
        ]
        
        for token in invalid_oauth_tokens:
            if token is not None:
                assert validate_oauth_token(token) is False, f"Should reject invalid OAuth token: {token}"
            else:
                with pytest.raises((TypeError, AttributeError)):
                    validate_oauth_token(token)

    def test_check_oauth_token_length_enforces_reasonable_bounds(self):
        """Test OAuth token length checker enforces reasonable length bounds."""
        # Too short
        assert _check_oauth_token_length("short") is False
        
        # Just right
        assert _check_oauth_token_length("reasonable_length_token") is True
        assert _check_oauth_token_length("x" * 2000) is True  # Maximum length
        
        # Too long
        assert _check_oauth_token_length("x" * 2001) is False


class TestErrorCodeValidation:
    """Test error code validation ensures consistent error handling."""

    def test_validate_error_code_accepts_valid_error_codes(self):
        """Test error code validator accepts valid error code formats."""
        valid_error_codes = [
            "UNAUTHORIZED",
            "TOKEN_EXPIRED",
            "INVALID_CREDENTIALS",
            "SERVICE_UNAVAILABLE",
            "RATE_LIMIT_EXCEEDED",
            "AUTH_FAILED"
        ]
        
        for code in valid_error_codes:
            assert validate_error_code(code) is True, f"Should accept valid error code: {code}"

    def test_validate_error_code_rejects_invalid_codes(self):
        """Test error code validator rejects invalid or malicious codes."""
        invalid_error_codes = [
            "",
            "lowercase_error",  # Should be uppercase
            "Mixed_Case_Error",  # Should be all uppercase
            "ERROR WITH SPACES",  # Spaces not allowed in underscore format
            "123_ERROR",  # Numbers not recommended at start
            "ERROR-WITH-DASHES",  # Dashes not allowed
            "ERROR; DROP TABLE errors;",  # SQL injection attempt
            "x" * 60,  # Too long
            None
        ]
        
        for code in invalid_error_codes:
            if code is not None:
                assert validate_error_code(code) is False, f"Should reject invalid error code: {code}"
            else:
                with pytest.raises((TypeError, AttributeError)):
                    validate_error_code(code)

    def test_check_error_code_length_prevents_dos_attacks(self):
        """Test error code length checker prevents DoS attacks."""
        # Reasonable length codes
        assert _check_error_code_length("AUTH_FAILED") is True
        assert _check_error_code_length("x" * 50) is True  # Maximum length
        
        # Oversized codes (potential DoS)
        assert _check_error_code_length("x" * 51) is False


class TestValidationErrorHandling:
    """Test validation error handling provides consistent, secure error responses."""

    def test_create_validation_error_creates_standardized_error(self):
        """Test validation error creator produces standardized error format."""
        error = create_validation_error("email", "Invalid email format")
        
        assert error["field"] == "email"
        assert error["message"] == "Invalid email format"
        assert error["code"] == "VALIDATION_ERROR"
        assert "timestamp" in error
        
        # Timestamp should be recent ISO format
        timestamp = datetime.fromisoformat(error["timestamp"].replace('Z', '+00:00'))
        assert isinstance(timestamp, datetime)

    def test_auth_validation_error_exception_provides_detailed_context(self):
        """Test AuthValidationError exception provides detailed error context."""
        error = AuthValidationError("password", "Password too weak", "WEAK_PASSWORD")
        
        assert error.field == "password"
        assert error.message == "Password too weak"
        assert error.code == "WEAK_PASSWORD"
        assert str(error) == "password: Password too weak"

    def test_validate_model_field_wrapper_handles_validation_gracefully(self):
        """Test model field validation wrapper handles validation errors gracefully."""
        # Valid field
        result = validate_model_field("test@example.com", "email", validate_email_format)
        assert result == "test@example.com"
        
        # Invalid field
        with pytest.raises(AuthValidationError) as exc_info:
            validate_model_field("invalid-email", "email", validate_email_format)
        
        assert exc_info.value.field == "email"
        assert "Invalid email" in exc_info.value.message

    def test_validate_model_field_handles_validator_exceptions(self):
        """Test model field validator handles exceptions from validator functions."""
        def failing_validator(value):
            raise ValueError("Validator error")
        
        with pytest.raises(AuthValidationError) as exc_info:
            validate_model_field("test", "field", failing_validator)
        
        assert exc_info.value.field == "field"
        assert "Validator error" in exc_info.value.message


class TestValidationBusinessValueDelivery:
    """Test that auth validators deliver the expected business value."""

    def test_validators_prevent_injection_attacks(self):
        """Test validators prevent common injection attack patterns."""
        injection_attempts = [
            ("email", "user@domain.com'; DROP TABLE users; --", validate_email_format),
            ("password", "pass'; DROP TABLE users; --", lambda p: validate_password_strength(p)["valid"]),
            ("service_id", "../admin; rm -rf /", validate_service_id),
            ("permission", "read; system('rm -rf /')", validate_permission_format)
        ]
        
        for field_name, malicious_input, validator in injection_attempts:
            result = validator(malicious_input)
            assert result is False, f"Should block injection in {field_name}: {malicious_input}"

    def test_validators_enforce_business_security_requirements(self):
        """Test validators enforce business-critical security requirements."""
        # Password requirements meet business security standards
        weak_password = validate_password_strength("weak")
        assert weak_password["valid"] is False
        
        strong_password = validate_password_strength("BusinessSecure123")
        assert strong_password["valid"] is True
        
        # Token validation prevents malformed attacks
        assert validate_token_format("malformed.token") is False
        assert validate_token_format("valid.jwt.token") is True

    def test_validators_support_multi_tenant_isolation(self):
        """Test validators support multi-tenant user isolation requirements."""
        # Service ID validation ensures proper inter-service auth
        assert validate_service_id("") is False  # Prevents empty service confusion
        assert validate_service_id("user-service") is True  # Supports tenant isolation
        
        # Permission validation supports role-based access control
        assert validate_permission_format("tenant1:read") is True
        assert validate_permission_format("tenant2:admin") is True

    def test_validators_prevent_dos_attacks(self):
        """Test validators prevent DoS attacks via input size limits."""
        # Prevent oversized inputs that could cause DoS
        oversized_inputs = [
            ("x" * 2000, validate_email_format, False),  # Oversized email
            ("x" * 300, validate_service_id, False),  # Oversized service ID
            ("x" * 200, validate_permission_format, False),  # Oversized permission
            ({"key": "x" * 2000}, validate_session_metadata, False)  # Oversized metadata
        ]
        
        for oversized_input, validator, expected_result in oversized_inputs:
            try:
                result = validator(oversized_input)
                assert result == expected_result, f"Should handle oversized input: {type(oversized_input)}"
            except (TypeError, AttributeError):
                # Some validators may raise exceptions for wrong types
                pass

    def test_validators_maintain_platform_consistency(self):
        """Test validators maintain consistent behavior across the platform."""
        # All validators should handle None gracefully (either reject or handle)
        validators_to_test = [
            validate_email_format,
            validate_service_id,
            validate_permission_format,
            validate_auth_provider,
            validate_token_type,
            validate_error_code,
            validate_endpoint_url
        ]
        
        for validator in validators_to_test:
            try:
                result = validator(None)
                # If it doesn't raise an exception, it should return False
                assert result is False, f"Validator {validator.__name__} should reject None"
            except (TypeError, AttributeError):
                # Raising an exception is also acceptable for None input
                pass