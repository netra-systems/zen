"""
Session Test Data Factory
Creates test sessions with proper expiration and metadata.
Supports both active and expired sessions for comprehensive testing.
"""

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from auth_service.auth_core.database.models import AuthSession


class SessionFactory:
    """Factory for creating test session data structures"""
    
    @staticmethod
    def create_session_data(
        user_id: str = None,
        ip_address: str = "127.0.0.1",
        user_agent: str = "pytest-test-client",
        device_id: str = None,
        expires_in_hours: int = 24,
        is_active: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Create session data dictionary"""
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        return {
            "id": session_id,
            "user_id": user_id or str(uuid.uuid4()),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "device_id": device_id or f"device_{uuid.uuid4().hex[:12]}",
            "created_at": now,
            "expires_at": now + timedelta(hours=expires_in_hours),
            "last_activity": now,
            "is_active": is_active,
            **kwargs
        }
    
    @staticmethod
    def create_active_session_data(user_id: str = None, **kwargs) -> Dict[str, Any]:
        """Create active session data"""
        return SessionFactory.create_session_data(
            user_id=user_id,
            is_active=True,
            **kwargs
        )
    
    @staticmethod
    def create_expired_session_data(user_id: str = None, **kwargs) -> Dict[str, Any]:
        """Create expired session data"""
        now = datetime.now(timezone.utc)
        
        return SessionFactory.create_session_data(
            user_id=user_id,
            expires_in_hours=-1,  # Expired 1 hour ago
            created_at=now - timedelta(hours=25),
            last_activity=now - timedelta(hours=2),
            **kwargs
        )
    
    @staticmethod
    def create_revoked_session_data(user_id: str = None, **kwargs) -> Dict[str, Any]:
        """Create revoked session data"""
        return SessionFactory.create_session_data(
            user_id=user_id,
            is_active=False,
            revoked_at=datetime.now(timezone.utc),
            **kwargs
        )
    
    @staticmethod
    def create_mobile_session_data(user_id: str = None, **kwargs) -> Dict[str, Any]:
        """Create mobile session data"""
        return SessionFactory.create_session_data(
            user_id=user_id,
            user_agent="Mobile App/1.0.0 (iOS 15.0)",
            device_id=f"ios_{uuid.uuid4().hex[:16]}",
            **kwargs
        )
    
    @staticmethod
    def create_web_session_data(user_id: str = None, **kwargs) -> Dict[str, Any]:
        """Create web browser session data"""
        return SessionFactory.create_session_data(
            user_id=user_id,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124",
            device_id=f"web_{uuid.uuid4().hex[:16]}",
            **kwargs
        )
    
    @staticmethod
    def create_refresh_token_hash(refresh_token: str) -> str:
        """Create hash for refresh token storage"""
        return hashlib.sha256(refresh_token.encode()).hexdigest()
    
    @staticmethod
    def create_session_with_refresh_token(
        user_id: str = None,
        refresh_token: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create session with refresh token hash"""
        if refresh_token is None:
            refresh_token = f"refresh_token_{uuid.uuid4().hex}"
        
        session_data = SessionFactory.create_session_data(user_id=user_id, **kwargs)
        session_data["refresh_token_hash"] = SessionFactory.create_refresh_token_hash(refresh_token)
        
        return session_data


class AuthSessionFactory:
    """Factory for creating AuthSession database model instances"""
    
    @staticmethod
    def create_session(session, user_id: str = None, **kwargs) -> AuthSession:
        """Create and save AuthSession to database"""
        session_data = SessionFactory.create_session_data(user_id=user_id, **kwargs)
        
        auth_session = AuthSession(**session_data)
        session.add(auth_session)
        return auth_session
    
    @staticmethod
    def create_active_session(session, user_id: str = None, **kwargs) -> AuthSession:
        """Create active session"""
        return AuthSessionFactory.create_session(
            session,
            user_id=user_id,
            is_active=True,
            **kwargs
        )
    
    @staticmethod
    def create_expired_session(session, user_id: str = None, **kwargs) -> AuthSession:
        """Create expired session"""
        session_data = SessionFactory.create_expired_session_data(user_id=user_id, **kwargs)
        
        auth_session = AuthSession(**session_data)
        session.add(auth_session)
        return auth_session
    
    @staticmethod
    def create_multiple_sessions(
        session,
        user_id: str,
        count: int = 3,
        **kwargs
    ) -> list[AuthSession]:
        """Create multiple sessions for a user"""
        sessions = []
        for i in range(count):
            session_kwargs = {
                **kwargs,
                "device_id": f"device_{i}_{uuid.uuid4().hex[:8]}"
            }
            auth_session = AuthSessionFactory.create_session(
                session,
                user_id=user_id,
                **session_kwargs
            )
            sessions.append(auth_session)
        
        return sessions
    
    @staticmethod
    def create_session_with_refresh_token(
        session,
        user_id: str = None,
        refresh_token: str = None,
        **kwargs
    ) -> tuple[AuthSession, str]:
        """Create session with refresh token, returns (session, refresh_token)"""
        if refresh_token is None:
            refresh_token = f"refresh_token_{uuid.uuid4().hex}"
        
        session_data = SessionFactory.create_session_with_refresh_token(
            user_id=user_id,
            refresh_token=refresh_token,
            **kwargs
        )
        
        auth_session = AuthSession(**session_data)
        session.add(auth_session)
        
        return auth_session, refresh_token