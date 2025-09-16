"""
Assertion Helpers for Auth Service Tests
Custom assertion functions for common auth testing scenarios.
Provides clear and reusable assertions with detailed error messages.
"""

import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from auth_service.auth_core.database.models import AuthUser, AuthSession
from auth_service.tests.factories import TokenFactory


class AssertionHelpers:
    """Custom assertion helpers for auth testing"""
    
    @staticmethod
    def assert_valid_email(email: str, message: str = None):
        """Assert email format is valid"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        assert re.match(email_pattern, email), \
            message or f"Invalid email format: {email}"
    
    @staticmethod
    def assert_valid_uuid(uuid_string: str, message: str = None):
        """Assert string is valid UUID format"""
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, uuid_string.lower()), \
            message or f"Invalid UUID format: {uuid_string}"
    
    @staticmethod
    def assert_valid_jwt_token(token: str, message: str = None):
        """Assert token is valid JWT format"""
        parts = token.split('.')
        assert len(parts) == 3, \
            message or f"Invalid JWT format: expected 3 parts, got {len(parts)}"
        
        # Verify each part is base64url encoded
        import base64
        for i, part in enumerate(parts):
            try:
                # Add padding if needed
                padded = part + '=' * (4 - len(part) % 4)
                base64.urlsafe_b64decode(padded)
            except Exception as e:
                assert False, f"Invalid base64url encoding in JWT part {i}: {e}"
    
    @staticmethod
    def assert_token_not_expired(token: str, message: str = None):
        """Assert JWT token is not expired"""
        try:
            TokenFactory.decode_token(token, verify=True)
        except Exception as e:
            if "expired" in str(e).lower():
                assert False, message or f"Token is expired: {e}"
            else:
                assert False, message or f"Token validation failed: {e}"
    
    @staticmethod
    def assert_token_expired(token: str, message: str = None):
        """Assert JWT token is expired"""
        try:
            TokenFactory.decode_token(token, verify=True)
            assert False, message or "Expected token to be expired, but it's valid"
        except Exception as e:
            if "expired" not in str(e).lower():
                assert False, message or f"Token failed for reason other than expiration: {e}"
    
    @staticmethod
    def assert_password_strength(password: str, min_length: int = 8):
        """Assert password meets strength requirements"""
        assert len(password) >= min_length, \
            f"Password too short: minimum {min_length} characters required"
        
        assert any(c.isupper() for c in password), \
            "Password must contain at least one uppercase letter"
        
        assert any(c.islower() for c in password), \
            "Password must contain at least one lowercase letter"
        
        assert any(c.isdigit() for c in password), \
            "Password must contain at least one digit"
        
        assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password), \
            "Password must contain at least one special character"
    
    @staticmethod
    def assert_user_data_valid(user_data: Dict[str, Any]):
        """Assert user data has required fields and valid values"""
        required_fields = ["id", "email", "auth_provider", "is_active"]
        
        for field in required_fields:
            assert field in user_data, f"Missing required field: {field}"
        
        AssertionHelpers.assert_valid_uuid(user_data["id"])
        AssertionHelpers.assert_valid_email(user_data["email"])
        
        assert isinstance(user_data["is_active"], bool), \
            "is_active must be boolean"
        
        # Validate auth provider
        valid_providers = ["local", "google", "github", "api_key"]
        assert user_data["auth_provider"] in valid_providers, \
            f"Invalid auth provider: {user_data['auth_provider']}"
    
    @staticmethod
    def assert_session_data_valid(session_data: Dict[str, Any]):
        """Assert session data has required fields and valid values"""
        required_fields = ["id", "user_id", "created_at", "expires_at", "is_active"]
        
        for field in required_fields:
            assert field in session_data, f"Missing required field: {field}"
        
        AssertionHelpers.assert_valid_uuid(session_data["id"])
        AssertionHelpers.assert_valid_uuid(session_data["user_id"])
        
        assert isinstance(session_data["is_active"], bool), \
            "is_active must be boolean"
        
        # Validate datetime fields
        created_at = session_data["created_at"]
        expires_at = session_data["expires_at"]
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        
        assert expires_at > created_at, \
            "Session expiration must be after creation time"
    
    @staticmethod
    def assert_login_response_valid(response: Dict[str, Any]):
        """Assert login response has required structure"""
        required_fields = ["access_token", "refresh_token", "token_type"]
        
        for field in required_fields:
            assert field in response, f"Missing required field in login response: {field}"
        
        assert response["token_type"] == "Bearer", \
            f"Expected token_type 'Bearer', got '{response['token_type']}'"
        
        AssertionHelpers.assert_valid_jwt_token(response["access_token"])
        AssertionHelpers.assert_valid_jwt_token(response["refresh_token"])
        
        # Verify tokens are not expired
        AssertionHelpers.assert_token_not_expired(response["access_token"])
        AssertionHelpers.assert_token_not_expired(response["refresh_token"])
    
    @staticmethod
    def assert_error_response_valid(
        response: Dict[str, Any],
        expected_status: int = None,
        expected_error_code: str = None
    ):
        """Assert error response has proper structure"""
        required_fields = ["error", "error_code", "message"]
        
        for field in required_fields:
            assert field in response, f"Missing required field in error response: {field}"
        
        if expected_status:
            assert response.get("status_code") == expected_status, \
                f"Expected status {expected_status}, got {response.get('status_code')}"
        
        if expected_error_code:
            assert response["error_code"] == expected_error_code, \
                f"Expected error code '{expected_error_code}', got '{response['error_code']}'"
    
    @staticmethod
    async def assert_user_exists_in_db(
        db_session: AsyncSession,
        user_id: str,
        expected_fields: Dict[str, Any] = None
    ):
        """Assert user exists in database with expected values"""
        user = await db_session.get(AuthUser, user_id)
        assert user is not None, f"User {user_id} not found in database"
        
        if expected_fields:
            for field, expected_value in expected_fields.items():
                actual_value = getattr(user, field, None)
                assert actual_value == expected_value, \
                    f"User.{field}: expected {expected_value}, got {actual_value}"
    
    @staticmethod
    async def assert_session_exists_in_db(
        db_session: AsyncSession,
        session_id: str,
        expected_fields: Dict[str, Any] = None
    ):
        """Assert session exists in database with expected values"""
        session = await db_session.get(AuthSession, session_id)
        assert session is not None, f"Session {session_id} not found in database"
        
        if expected_fields:
            for field, expected_value in expected_fields.items():
                actual_value = getattr(session, field, None)
                assert actual_value == expected_value, \
                    f"Session.{field}: expected {expected_value}, got {actual_value}"
    
    @staticmethod
    def assert_permissions_valid(
        permissions: List[str],
        required_permissions: List[str] = None,
        forbidden_permissions: List[str] = None
    ):
        """Assert permissions list is valid"""
        assert isinstance(permissions, list), "Permissions must be a list"
        
        # Check permission format
        permission_pattern = r'^[a-zA-Z_]+:[a-zA-Z_]+$'
        for perm in permissions:
            assert re.match(permission_pattern, perm), \
                f"Invalid permission format: {perm} (expected format: resource:action)"
        
        # Check required permissions are present
        if required_permissions:
            for required_perm in required_permissions:
                assert required_perm in permissions, \
                    f"Missing required permission: {required_perm}"
        
        # Check forbidden permissions are not present
        if forbidden_permissions:
            for forbidden_perm in forbidden_permissions:
                assert forbidden_perm not in permissions, \
                    f"Forbidden permission found: {forbidden_perm}"
    
    @staticmethod
    def assert_rate_limit_not_exceeded(
        response: Dict[str, Any],
        expected_remaining: int = None
    ):
        """Assert rate limit headers are present and valid"""
        headers = response.get("headers", {})
        
        assert "X-RateLimit-Limit" in headers, "Missing rate limit header"
        assert "X-RateLimit-Remaining" in headers, "Missing rate limit remaining header"
        assert "X-RateLimit-Reset" in headers, "Missing rate limit reset header"
        
        remaining = int(headers["X-RateLimit-Remaining"])
        assert remaining >= 0, f"Invalid rate limit remaining: {remaining}"
        
        if expected_remaining is not None:
            assert remaining == expected_remaining, \
                f"Expected {expected_remaining} remaining requests, got {remaining}"
    
    @staticmethod
    def assert_audit_log_entry(
        log_entry: Dict[str, Any],
        expected_event_type: str,
        expected_success: bool = True,
        expected_user_id: str = None
    ):
        """Assert audit log entry has expected structure and values"""
        required_fields = ["id", "event_type", "success", "created_at"]
        
        for field in required_fields:
            assert field in log_entry, f"Missing required field in audit log: {field}"
        
        assert log_entry["event_type"] == expected_event_type, \
            f"Expected event type '{expected_event_type}', got '{log_entry['event_type']}'"
        
        assert log_entry["success"] == expected_success, \
            f"Expected success={expected_success}, got {log_entry['success']}"
        
        if expected_user_id:
            assert log_entry.get("user_id") == expected_user_id, \
                f"Expected user_id '{expected_user_id}', got '{log_entry.get('user_id')}'"