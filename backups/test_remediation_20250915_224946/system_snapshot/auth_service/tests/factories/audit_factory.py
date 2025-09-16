"""
Audit Log Test Data Factory
Creates audit log entries for testing authentication events and security monitoring.
Supports various event types with proper metadata and tracking.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from auth_service.auth_core.database.models import AuthAuditLog


class AuditLogFactory:
    """Factory for creating test audit log entries"""
    
    # Standard event types
    EVENT_TYPES = {
        "LOGIN_SUCCESS": "login_success",
        "LOGIN_FAILED": "login_failed",
        "LOGOUT": "logout",
        "PASSWORD_CHANGE": "password_change",
        "PASSWORD_RESET": "password_reset",
        "ACCOUNT_LOCKED": "account_locked",
        "ACCOUNT_UNLOCKED": "account_unlocked",
        "TOKEN_CREATED": "token_created",
        "TOKEN_REFRESHED": "token_refreshed",
        "TOKEN_REVOKED": "token_revoked",
        "SESSION_CREATED": "session_created",
        "SESSION_EXPIRED": "session_expired",
        "PERMISSION_GRANTED": "permission_granted",
        "PERMISSION_REVOKED": "permission_revoked",
        "OAUTH_CALLBACK": "oauth_callback",
        "OAUTH_ERROR": "oauth_error"
    }
    
    @staticmethod
    def create_audit_data(
        event_type: str = "login_attempt",
        user_id: str = None,
        success: bool = True,
        ip_address: str = "127.0.0.1",
        user_agent: str = "pytest-test-client",
        error_message: str = None,
        metadata: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create audit log data dictionary"""
        return {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "user_id": user_id,
            "success": success,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "error_message": error_message,
            "event_metadata": metadata or {},
            "created_at": datetime.now(timezone.utc),
            **kwargs
        }
    
    @staticmethod
    def create_login_success_data(
        user_id: str = None,
        auth_provider: str = "local",
        **kwargs
    ) -> Dict[str, Any]:
        """Create successful login audit entry"""
        return AuditLogFactory.create_audit_data(
            event_type=AuditLogFactory.EVENT_TYPES["LOGIN_SUCCESS"],
            user_id=user_id or str(uuid.uuid4()),
            success=True,
            metadata={
                "auth_provider": auth_provider,
                "login_method": "password" if auth_provider == "local" else "oauth"
            },
            **kwargs
        )
    
    @staticmethod
    def create_login_failed_data(
        user_id: str = None,
        error_message: str = "Invalid credentials",
        attempt_number: int = 1,
        **kwargs
    ) -> Dict[str, Any]:
        """Create failed login audit entry"""
        return AuditLogFactory.create_audit_data(
            event_type=AuditLogFactory.EVENT_TYPES["LOGIN_FAILED"],
            user_id=user_id,
            success=False,
            error_message=error_message,
            metadata={
                "attempt_number": attempt_number,
                "failure_reason": error_message
            },
            **kwargs
        )
    
    @staticmethod
    def create_logout_data(user_id: str = None, **kwargs) -> Dict[str, Any]:
        """Create logout audit entry"""
        return AuditLogFactory.create_audit_data(
            event_type=AuditLogFactory.EVENT_TYPES["LOGOUT"],
            user_id=user_id or str(uuid.uuid4()),
            success=True,
            metadata={"logout_type": "user_initiated"},
            **kwargs
        )
    
    @staticmethod
    def create_password_change_data(
        user_id: str = None,
        success: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Create password change audit entry"""
        return AuditLogFactory.create_audit_data(
            event_type=AuditLogFactory.EVENT_TYPES["PASSWORD_CHANGE"],
            user_id=user_id or str(uuid.uuid4()),
            success=success,
            metadata={"change_method": "user_initiated"},
            **kwargs
        )
    
    @staticmethod
    def create_token_created_data(
        user_id: str = None,
        token_type: str = "access",
        **kwargs
    ) -> Dict[str, Any]:
        """Create token creation audit entry"""
        return AuditLogFactory.create_audit_data(
            event_type=AuditLogFactory.EVENT_TYPES["TOKEN_CREATED"],
            user_id=user_id or str(uuid.uuid4()),
            success=True,
            metadata={
                "token_type": token_type,
                "creation_method": "login"
            },
            **kwargs
        )
    
    @staticmethod
    def create_session_created_data(
        user_id: str = None,
        session_id: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create session creation audit entry"""
        return AuditLogFactory.create_audit_data(
            event_type=AuditLogFactory.EVENT_TYPES["SESSION_CREATED"],
            user_id=user_id or str(uuid.uuid4()),
            success=True,
            metadata={
                "session_id": session_id or str(uuid.uuid4()),
                "session_type": "web"
            },
            **kwargs
        )
    
    @staticmethod
    def create_oauth_callback_data(
        user_id: str = None,
        provider: str = "google",
        success: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Create OAuth callback audit entry"""
        return AuditLogFactory.create_audit_data(
            event_type=AuditLogFactory.EVENT_TYPES["OAUTH_CALLBACK"],
            user_id=user_id,
            success=success,
            metadata={
                "oauth_provider": provider,
                "callback_result": "success" if success else "error"
            },
            **kwargs
        )
    
    @staticmethod
    def create_account_locked_data(
        user_id: str = None,
        reason: str = "too_many_failed_attempts",
        **kwargs
    ) -> Dict[str, Any]:
        """Create account locked audit entry"""
        return AuditLogFactory.create_audit_data(
            event_type=AuditLogFactory.EVENT_TYPES["ACCOUNT_LOCKED"],
            user_id=user_id or str(uuid.uuid4()),
            success=True,
            metadata={
                "lock_reason": reason,
                "automated": True
            },
            **kwargs
        )
    
    @staticmethod
    def create_permission_granted_data(
        user_id: str = None,
        permission: str = "user:read_profile",
        granted_by: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create permission granted audit entry"""
        return AuditLogFactory.create_audit_data(
            event_type=AuditLogFactory.EVENT_TYPES["PERMISSION_GRANTED"],
            user_id=user_id or str(uuid.uuid4()),
            success=True,
            metadata={
                "permission": permission,
                "granted_by": granted_by or "system",
                "grant_method": "role_assignment"
            },
            **kwargs
        )
    
    @staticmethod
    def create_multiple_failed_attempts(
        user_id: str = None,
        count: int = 3,
        **kwargs
    ) -> list[Dict[str, Any]]:
        """Create multiple failed login attempts"""
        attempts = []
        for i in range(count):
            attempt = AuditLogFactory.create_login_failed_data(
                user_id=user_id,
                attempt_number=i + 1,
                **kwargs
            )
            attempts.append(attempt)
        return attempts


class AuthAuditLogFactory:
    """Factory for creating AuthAuditLog database model instances"""
    
    @staticmethod
    def create_audit_log(session, **kwargs) -> AuthAuditLog:
        """Create and save AuthAuditLog to database"""
        audit_data = AuditLogFactory.create_audit_data(**kwargs)
        
        audit_log = AuthAuditLog(**audit_data)
        session.add(audit_log)
        return audit_log
    
    @staticmethod
    def create_login_success(session, user_id: str = None, **kwargs) -> AuthAuditLog:
        """Create successful login audit log"""
        audit_data = AuditLogFactory.create_login_success_data(user_id=user_id, **kwargs)
        
        audit_log = AuthAuditLog(**audit_data)
        session.add(audit_log)
        return audit_log
    
    @staticmethod
    def create_login_failed(session, user_id: str = None, **kwargs) -> AuthAuditLog:
        """Create failed login audit log"""
        audit_data = AuditLogFactory.create_login_failed_data(user_id=user_id, **kwargs)
        
        audit_log = AuthAuditLog(**audit_data)
        session.add(audit_log)
        return audit_log
    
    @staticmethod
    def create_multiple_audit_logs(
        session,
        audit_data_list: list[Dict[str, Any]]
    ) -> list[AuthAuditLog]:
        """Create multiple audit logs from data list"""
        audit_logs = []
        for audit_data in audit_data_list:
            audit_log = AuthAuditLog(**audit_data)
            session.add(audit_log)
            audit_logs.append(audit_log)
        
        return audit_logs