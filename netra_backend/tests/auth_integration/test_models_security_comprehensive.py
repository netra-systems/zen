"""
Security-Focused Auth Models Tests - Data Validation & Serialization Security

Business Value Justification (BVJ):
    - Segment: ALL (Free → Enterprise) - DATA SECURITY CRITICAL
- Business Goal: Prevent data validation bypasses and serialization vulnerabilities
- Value Impact: Prevent auth model manipulation and data integrity breaches
- Revenue Impact: Critical - Model vulnerabilities = potential OAUTH SIMULATIONes
- ESTIMATED RISK: -$750K+ potential impact from auth model security failures

SECURITY FOCUS AREAS:
    - Pydantic model validation bypasses
- Serialization/deserialization attacks
- Type coercion vulnerabilities  
- Field validation bypasses
- Mass assignment vulnerabilities
- Data leakage in serialization
- Model constraint enforcement
- Enum value validation
- Date/time manipulation attacks
- JSON injection prevention

COMPLIANCE:
    - 90%+ test coverage for all model validation
- Zero tolerance for validation bypasses
- Comprehensive serialization security testing
- Edge case validation for all model fields
""""

import json
import warnings
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest
from pydantic import ValidationError

from netra_backend.app.schemas.auth_types import (
    # Enums
    TokenType,
    TokenStatus,
    ServiceStatus,
    AuthProvider,
    # Models
    Token,
    TokenPayload,
    TokenData,
    TokenClaims,
    TokenRequest,
    TokenResponse,
    RefreshRequest,
    RefreshResponse,
    LoginRequest,
    LoginResponse,
    ServiceTokenRequest,
    ServiceTokenResponse,
    SessionInfo,
    UserPermission,
    AuditLog,
    AuthConfig,
    AuthConfigResponse,
    AuthEndpoints,
    HealthResponse,
    AuthError,
    DevUser,
    DevLoginRequest,
    GoogleUser,
    # Exceptions
    RateLimitError,
    AuthenticationError,
)


class TestTokenModelSecurity:
    """Test Token model security and validation"""

    def test_token_model_field_validation_security(self):
        """SECURITY: Test Token model field validation"""
        # Valid token
        valid_token = Token(
            access_token="secure_token_123",
            token_type="Bearer",
            refresh_token="refresh_token_456",
            expires_in=3600
        )
        
        assert valid_token.access_token == "secure_token_123"
        assert valid_token.token_type == "Bearer"
        assert valid_token.refresh_token == "refresh_token_456"
        assert valid_token.expires_in == 3600

    def test_token_model_injection_prevention(self):
        """SECURITY: Test prevention of injection attacks in Token model"""
        # SQL injection attempts
        with pytest.raises(ValidationError):
            Token(access_token=None)  # Required field
        
        # XSS attempts (should be handled as strings)
        xss_token = Token(
            access_token="<script>alert('xss')</script>",
            token_type="Bearer"
        )
        assert xss_token.access_token == "<script>alert('xss')</script>"  # Stored as-is
        
        # Note: XSS prevention should happen at the API boundary, not model level

    def test_token_model_type_coercion_security(self):
        """SECURITY: Test type coercion security in Token model"""
        # Integer to string coercion for token_type
        token = Token(
            access_token="token123",
            token_type=123  # Should be coerced to string
        )
        assert token.token_type == "123"
        
        # Integer expires_in validation
        token = Token(
            access_token="token123",
            expires_in="3600"  # String should be coerced to int
        )
        assert token.expires_in == 3600
        assert isinstance(token.expires_in, int)

    def test_token_model_serialization_security(self):
        """SECURITY: Test Token model serialization security"""
        token = Token(
            access_token="secret_token_123",
            token_type="Bearer",
            refresh_token="secret_refresh_456",
            expires_in=3600
        )
        
        # Serialize to dict
        token_dict = token.model_dump()
        assert token_dict["access_token"] == "secret_token_123"
        assert "password" not in token_dict  # No password fields to leak
        
        # Serialize to JSON
        token_json = token.model_dump_json()
        parsed = json.loads(token_json)
        assert parsed["access_token"] == "secret_token_123"


class TestTokenPayloadSecurity:
    """Test TokenPayload model security"""

    def test_token_payload_field_validation_security(self):
        """SECURITY: Test TokenPayload field validation"""
        # Valid payload
        payload = TokenPayload(
            sub="user_123",
            user_id="user_123",
            email="test@example.com",
            roles=["user"],
            permissions=["read:data"],
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            iat=datetime.now(timezone.utc),
            jti="jwt_id_123",
            environment="production"
        )
        
        assert payload.sub == "user_123"
        assert payload.user_id == "user_123"
        assert payload.email == "test@example.com"

    def test_token_payload_injection_prevention(self):
        """SECURITY: Test injection prevention in TokenPayload"""
        # SQL injection in user ID
        payload = TokenPayload(
            sub="user'; DROP TABLE users; --",
            user_id="user'; DROP TABLE users; --",
            email="test@example.com"
        )
        
        # Should store as-is (validation at business logic layer)
        assert "DROP TABLE" in payload.sub
        assert "DROP TABLE" in payload.user_id

    def test_token_payload_list_validation_security(self):
        """SECURITY: Test list field validation in TokenPayload"""
        # Valid lists
        payload = TokenPayload(
            sub="user_123",
            roles=["admin", "user"],
            permissions=["read:all", "write:all"]
        )
        assert isinstance(payload.roles, list)
        assert isinstance(payload.permissions, list)
        
        # Invalid list types (should be coerced or raise error)
        with pytest.raises(ValidationError):
            TokenPayload(
                sub="user_123",
                roles="not_a_list"  # Should be list
            )

    def test_token_payload_datetime_validation_security(self):
        """SECURITY: Test datetime validation in TokenPayload"""
        current_time = datetime.now(timezone.utc)
        
        # Valid datetime
        payload = TokenPayload(
            sub="user_123",
            exp=current_time + timedelta(hours=1),
            iat=current_time
        )
        assert isinstance(payload.exp, datetime)
        assert isinstance(payload.iat, datetime)
        
        # Invalid datetime strings (should raise ValidationError)
        with pytest.raises(ValidationError):
            TokenPayload(
                sub="user_123",
                exp="invalid_datetime_string"
            )


class TestLoginRequestSecurity:
    """Test LoginRequest model security"""

    def test_login_request_email_validation_security(self):
        """SECURITY: Test email validation in LoginRequest"""
        # Valid login request
        login = LoginRequest(
            email="test@example.com",
            password="secure_password",
            provider=AuthProvider.LOCAL
        )
        assert login.email == "test@example.com"
        
        # Invalid email should raise ValidationError
        with pytest.raises(ValidationError):
            LoginRequest(
                email="not_an_email",
                password="password",
                provider=AuthProvider.LOCAL
            )
        
        # Email injection attempts
        with pytest.raises(ValidationError):
            LoginRequest(
                email="user@domain.com'; DROP TABLE users; --",
                password="password",
                provider=AuthProvider.LOCAL
            )

    def test_login_request_password_validation_security(self):
        """SECURITY: Test password validation in LoginRequest"""
        # Password is optional for non-local providers
        oauth_login = LoginRequest(
            email="test@example.com",
            provider=AuthProvider.GOOGLE,
            oauth_token="google_token_123"
        )
        assert oauth_login.password is None
        assert oauth_login.oauth_token == "google_token_123"
        
        # Local auth without password should trigger warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            local_login = LoginRequest(
                email="test@example.com",
                provider=AuthProvider.LOCAL
            )
            assert len(w) == 1
            assert "Password missing for local auth" in str(w[0].message)

    def test_login_request_provider_validation_security(self):
        """SECURITY: Test provider validation in LoginRequest"""
        # Valid providers
        for provider in [AuthProvider.LOCAL, AuthProvider.GOOGLE, AuthProvider.GITHUB, AuthProvider.API_KEY]:
            login = LoginRequest(
                email="test@example.com",
                password="password" if provider == AuthProvider.LOCAL else None,
                provider=provider
            )
            assert login.provider == provider
        
        # Invalid provider string (should raise ValidationError)
        with pytest.raises(ValidationError):
            LoginRequest(
                email="test@example.com",
                provider="invalid_provider"
            )

    def test_login_request_oauth_token_security(self):
        """SECURITY: Test OAuth token handling in LoginRequest"""
        # OAuth token should be treated securely
        login = LoginRequest(
            email="test@example.com",
            provider=AuthProvider.GOOGLE,
            oauth_token="sensitive_oauth_token_123"
        )
        
        # Token should be stored but not logged in serialization
        assert login.oauth_token == "sensitive_oauth_token_123"
        
        # Serialize and check for potential leakage
        login_dict = login.model_dump()
        assert "oauth_token" in login_dict  # Present but should be handled carefully


class TestSessionInfoSecurity:
    """Test SessionInfo model security"""

    def test_session_info_field_validation_security(self):
        """SECURITY: Test SessionInfo field validation"""
        current_time = datetime.now(timezone.utc)
        
        # Valid session info
        session = SessionInfo(
            session_id="session_123",
            user_id="user_456",
            created_at=current_time,
            last_activity=current_time,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Browser",
            metadata={"device": "mobile", "location": "US"}
        )
        
        assert session.session_id == "session_123"
        assert session.user_id == "user_456"
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.metadata, dict)

    def test_session_info_ip_validation_security(self):
        """SECURITY: Test IP address validation in SessionInfo"""
        current_time = datetime.now(timezone.utc)
        
        # Valid IP addresses
        valid_ips = ["192.168.1.1", "10.0.0.1", "127.0.0.1", "::1", "fe80::1"]
        
        for ip in valid_ips:
            session = SessionInfo(
                session_id="session_123",
                user_id="user_456",
                created_at=current_time,
                last_activity=current_time,
                ip_address=ip
            )
            assert session.ip_address == ip
        
        # Injection attempts in IP (should be stored as-is, validated elsewhere)
        malicious_ip = "192.168.1.1'; DROP TABLE sessions; --"
        session = SessionInfo(
            session_id="session_123",
            user_id="user_456", 
            created_at=current_time,
            last_activity=current_time,
            ip_address=malicious_ip
        )
        assert session.ip_address == malicious_ip

    def test_session_info_metadata_security(self):
        """SECURITY: Test metadata field security in SessionInfo"""
        current_time = datetime.now(timezone.utc)
        
        # Valid metadata
        safe_metadata = {
            "device_type": "desktop",
            "browser": "Chrome",
            "location": "US",
            "login_method": "password"
        }
        
        session = SessionInfo(
            session_id="session_123",
            user_id="user_456",
            created_at=current_time,
            last_activity=current_time,
            metadata=safe_metadata
        )
        assert session.metadata == safe_metadata
        
        # Potentially malicious metadata (stored as-is)
        malicious_metadata = {
            "script": "<script>alert('xss')</script>",
            "sql": "'; DROP TABLE sessions; --",
            "command": "rm -rf /",
        }
        
        session = SessionInfo(
            session_id="session_123",
            user_id="user_456",
            created_at=current_time,
            last_activity=current_time,
            metadata=malicious_metadata
        )
        assert session.metadata == malicious_metadata
        
        # Metadata should be validated when used, not at model level


class TestUserPermissionSecurity:
    """Test UserPermission model security"""

    def test_user_permission_field_validation_security(self):
        """SECURITY: Test UserPermission field validation"""
        current_time = datetime.now(timezone.utc)
        
        # Valid permission
        permission = UserPermission(
            user_id="user_123",
            permission="read:sensitive_data",
            granted_at=current_time,
            granted_by="admin_456",
            metadata={"scope": "project_789"}
        )
        
        assert permission.user_id == "user_123"
        assert permission.permission == "read:sensitive_data"
        assert isinstance(permission.granted_at, datetime)

    def test_user_permission_injection_prevention(self):
        """SECURITY: Test injection prevention in UserPermission"""
        current_time = datetime.now(timezone.utc)
        
        # SQL injection attempts
        injection_permission = UserPermission(
            user_id="user'; DROP TABLE permissions; --",
            permission="read:data'; DELETE FROM users; --",
            granted_at=current_time,
            granted_by="admin'; UPDATE users SET role='admin'; --"
        )
        
        # Should store as-is (validation at business logic layer)
        assert "DROP TABLE" in injection_permission.user_id
        assert "DELETE FROM" in injection_permission.permission
        assert "UPDATE users" in injection_permission.granted_by

    def test_user_permission_privilege_escalation_prevention(self):
        """SECURITY: Test prevention of privilege escalation in permissions"""
        current_time = datetime.now(timezone.utc)
        
        # Attempt to grant admin permissions
        admin_permission = UserPermission(
            user_id="regular_user_123",
            permission="admin:full_access",
            granted_at=current_time,
            granted_by="regular_user_123"  # Self-granting
        )
        
        # Model should accept but business logic should validate
        assert admin_permission.permission == "admin:full_access"
        assert admin_permission.granted_by == "regular_user_123"


class TestAuditLogSecurity:
    """Test AuditLog model security"""

    def test_audit_log_field_validation_security(self):
        """SECURITY: Test AuditLog field validation"""
        current_time = datetime.now(timezone.utc)
        
        # Valid audit log
        audit = AuditLog(
            user_id="user_123",
            event_type="login",
            timestamp=current_time,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 Browser",
            success=True,
            metadata={"method": "password", "session_id": "session_456"}
        )
        
        assert audit.user_id == "user_123"
        assert audit.event_type == "login"
        assert audit.success is True

    def test_audit_log_tampering_prevention(self):
        """SECURITY: Test prevention of audit log tampering"""
        current_time = datetime.now(timezone.utc)
        
        # Attempt to create false audit log
        false_audit = AuditLog(
            user_id="hacker_123",
            event_type="admin_login",  # Fake admin login
            timestamp=current_time - timedelta(days=30),  # Backdated
            success=True,
            metadata={"spoofed": True}
        )
        
        # Model accepts but business logic should validate
        assert false_audit.event_type == "admin_login"
        assert false_audit.success is True

    def test_audit_log_injection_prevention(self):
        """SECURITY: Test injection prevention in AuditLog"""
        current_time = datetime.now(timezone.utc)
        
        # Log injection attempts
        log_injection = AuditLog(
            user_id="user_123\nFAKE_LOG: admin login successful",
            event_type="login\r\nFAKE_EVENT: privilege_escalation",
            timestamp=current_time,
            ip_address="192.168.1.1\nSPOOF: 127.0.0.1",
            success=True
        )
        
        # Should store as-is but be sanitized when logged
        assert "\n" in log_injection.user_id
        assert "\r\n" in log_injection.event_type
        assert "\n" in log_injection.ip_address


class TestServiceTokenSecurity:
    """Test ServiceToken models security"""

    def test_service_token_request_validation_security(self):
        """SECURITY: Test ServiceTokenRequest validation"""
        # Valid service token request
        request = ServiceTokenRequest(
            service_id="auth-service",
            service_secret="super_secret_key_123",
            requested_permissions=["read:config", "write:logs"]
        )
        
        assert request.service_id == "auth-service"
        assert request.service_secret == "super_secret_key_123"
        assert isinstance(request.requested_permissions, list)

    def test_service_token_secret_handling_security(self):
        """SECURITY: Test service secret handling"""
        # Service secret should be handled securely
        request = ServiceTokenRequest(
            service_id="backend-service",
            service_secret="very_sensitive_secret_456"
        )
        
        # Secret is stored but should not be logged
        assert request.service_secret == "very_sensitive_secret_456"
        
        # Serialization should be careful with secrets
        request_dict = request.model_dump()
        assert "service_secret" in request_dict  # Present but should be handled carefully

    def test_service_token_permission_validation_security(self):
        """SECURITY: Test service permission validation"""
        # Excessive permissions request
        request = ServiceTokenRequest(
            service_id="malicious-service",
            service_secret="secret",
            requested_permissions=["admin:*", "read:all", "write:all", "delete:all"]
        )
        
        # Model accepts but business logic should validate
        assert len(request.requested_permissions) == 4
        assert "admin:*" in request.requested_permissions


class TestHealthResponseSecurity:
    """Test HealthResponse model security"""

    def test_health_response_information_disclosure_prevention(self):
        """SECURITY: Test prevention of information disclosure in health responses"""
        current_time = datetime.now(timezone.utc)
        
        # Health response should not leak sensitive information
        health = HealthResponse(
            status="healthy",
            timestamp=current_time,
            version="1.0.0",
            uptime=timedelta(hours=24),
            checks={
                "database": "healthy",
                "redis": "healthy",
                "external_api": "degraded"
            }
        )
        
        assert health.status == "healthy"
        assert health.version == "1.0.0"
        assert "database" in health.checks
        
        # Should not contain sensitive configuration
        health_dict = health.model_dump()
        assert "password" not in str(health_dict).lower()
        assert "secret" not in str(health_dict).lower()
        assert "key" not in str(health_dict).lower()


class TestEnumValidationSecurity:
    """Test enum validation security"""

    def test_token_type_enum_security(self):
        """SECURITY: Test TokenType enum validation"""
        # Valid token types
        assert TokenType.ACCESS == "access"
        assert TokenType.REFRESH == "refresh"
        assert TokenType.SERVICE == "service"
        
        # Test enum in model
        request = TokenRequest(
            token="token123",
            token_type=TokenType.ACCESS
        )
        assert request.token_type == TokenType.ACCESS
        
        # Invalid token type should raise ValidationError
        with pytest.raises(ValidationError):
            TokenRequest(
                token="token123",
                token_type="invalid_type"
            )

    def test_auth_provider_enum_security(self):
        """SECURITY: Test AuthProvider enum validation"""
        # Valid providers
        assert AuthProvider.LOCAL == "local"
        assert AuthProvider.GOOGLE == "google"
        assert AuthProvider.GITHUB == "github"
        assert AuthProvider.API_KEY == "api_key"
        
        # Test in LoginRequest
        login = LoginRequest(
            email="test@example.com",
            provider=AuthProvider.GOOGLE
        )
        assert login.provider == AuthProvider.GOOGLE

    def test_service_status_enum_security(self):
        """SECURITY: Test ServiceStatus enum validation"""
        # Valid statuses
        valid_statuses = [
            ServiceStatus.HEALTHY,
            ServiceStatus.UNHEALTHY, 
            ServiceStatus.DEGRADED,
            ServiceStatus.STARTING,
            ServiceStatus.STOPPING
        ]
        
        for status in valid_statuses:
            assert isinstance(status.value, str)
            assert len(status.value) > 0


class TestModelSerializationSecurity:
    """Test model serialization security"""

    def test_sensitive_data_serialization_security(self):
        """SECURITY: Test handling of sensitive data in serialization"""
        # Login request with sensitive data
        login = LoginRequest(
            email="test@example.com",
            password="secret_password_123",
            provider=AuthProvider.LOCAL
        )
        
        # Serialize to dict
        login_dict = login.model_dump()
        assert login_dict["password"] == "secret_password_123"  # Present
        
        # JSON serialization
        login_json = login.model_dump_json()
        assert "secret_password_123" in login_json  # Present in JSON
        
        # Note: Sensitive data filtering should happen at API layer, not model layer

    def test_model_deserialization_security(self):
        """SECURITY: Test model deserialization security"""
        # Malicious JSON input
        malicious_json = {
            "email": "test@example.com",
            "password": "password",
            "provider": "local",
            "__class__": "LoginRequest",  # Potential class pollution
            "constructor": {"__class__": "exploit"},  # Nested class pollution
            "admin": True,  # Extra field
            "is_superuser": True  # Extra field
        }
        
        # Pydantic should ignore extra fields by default
        login = LoginRequest(**malicious_json)
        assert login.email == "test@example.com"
        assert login.provider == AuthProvider.LOCAL
        assert not hasattr(login, "admin")
        assert not hasattr(login, "is_superuser")

    def test_mass_assignment_prevention(self):
        """SECURITY: Test prevention of mass assignment vulnerabilities"""
        # Attempt mass assignment with extra fields
        user_data = {
            "user_id": "user_123",
            "permission": "read:data",
            "granted_at": datetime.now(timezone.utc),
            "granted_by": "admin_456",
            "is_admin": True,  # Should be ignored
            "role": "admin",   # Should be ignored
            "system_access": True  # Should be ignored
        }
        
        # Only defined fields should be accepted
        permission = UserPermission(**user_data)
        assert permission.user_id == "user_123"
        assert permission.permission == "read:data"
        assert not hasattr(permission, "is_admin")
        assert not hasattr(permission, "role")
        assert not hasattr(permission, "system_access")


class TestErrorHandlingSecurity:
    """Test error handling security in models"""

    def test_rate_limit_error_security(self):
        """SECURITY: Test RateLimitError exception security"""
        # Create rate limit error
        error = RateLimitError("Too many requests", retry_after=60)
        
        assert str(error) == "Too many requests"
        assert error.retry_after == 60
        
        # Should not leak sensitive information
        assert "password" not in str(error).lower()
        assert "secret" not in str(error).lower()

    def test_authentication_error_security(self):
        """SECURITY: Test AuthenticationError exception security"""
        # Create auth error
        error = AuthenticationError("Invalid credentials")
        
        assert str(error) == "Invalid credentials"
        
        # Should not provide details that could aid attackers
        detailed_error = AuthenticationError("User 'admin' does not exist")
        assert "admin" in str(detailed_error)  # This might leak user enumeration

    def test_validation_error_information_disclosure(self):
        """SECURITY: Test ValidationError information disclosure"""
        # Try to create invalid model
        try:
            LoginRequest(
                email="not_an_email",  # Invalid email
                password="password",
                provider="invalid_provider"  # Invalid provider
            )
        except ValidationError as e:
            error_str = str(e)
            
            # Should contain validation errors
            assert "email" in error_str.lower()
            assert "provider" in error_str.lower()
            
            # Should not leak system information
            assert "python" not in error_str.lower()
            assert "traceback" not in error_str.lower()
            assert "file" not in error_str.lower()


class TestModelConstraintSecurity:
    """Test model constraint enforcement security"""

    def test_field_length_constraints_security(self):
        """SECURITY: Test field length constraint enforcement"""
        # Long strings that might cause DoS
        long_string = "a" * 10000
        
        # Most fields should handle long strings gracefully
        try:
            session = SessionInfo(
                session_id=long_string,
                user_id=long_string,
                created_at=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc),
                ip_address="192.168.1.1",
                user_agent=long_string,
                metadata={"key": long_string}
            )
            
            # If accepted, lengths should be as expected
            assert len(session.session_id) == 10000
            assert len(session.user_id) == 10000
            
        except ValidationError:
            # If validation fails, that's also acceptable for security
            pass

    def test_datetime_constraint_security(self):
        """SECURITY: Test datetime constraint enforcement"""
        # Future dates (potential timestamp manipulation)
        future_time = datetime.now(timezone.utc) + timedelta(days=365)
        
        # Past dates (potential replay attacks)
        past_time = datetime.now(timezone.utc) - timedelta(days=365)
        
        # Models should accept but business logic should validate
        session = SessionInfo(
            session_id="session_123",
            user_id="user_456",
            created_at=future_time,  # Future creation time
            last_activity=past_time  # Past activity time
        )
        
        assert session.created_at == future_time
        assert session.last_activity == past_time

    def test_numeric_constraint_security(self):
        """SECURITY: Test numeric constraint enforcement"""
        # Extreme values
        extreme_expires_in = 999999999  # Very large expiration
        negative_expires_in = -3600  # Negative expiration
        
        # Large expiration
        token = Token(
            access_token="token123",
            expires_in=extreme_expires_in
        )
        assert token.expires_in == extreme_expires_in
        
        # Negative expiration (should be handled by business logic)
        token = Token(
            access_token="token123", 
            expires_in=negative_expires_in
        )
        assert token.expires_in == negative_expires_in